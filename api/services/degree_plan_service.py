"""
DEGREE PLAN VALIDATION SERVICE (CONCENTRATION-AWARE VERSION)
------------------------------------------------------------
Major Enhancements:
- Full concentration detection
- BBA requires 2 concentrations
- Other degrees require 1 (if concentrations exist)
- Concentration course matching
- Hours satisfied calculation
- Clean LLM-compatible output
"""

import math
import re
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from types import SimpleNamespace

from fastapi import BackgroundTasks, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from db.database import SessionLocal
from models.advisee import AdviseeProfile
from models.degree_plan import (
    AdviseeDegreeContext,
    DegreePlanValidation,
    DegreeRequirementSet,
    ValidationRunType,
    ValidationStatus,
)
from schemas.degree_plan import (
    AdviseeContextUpsert,
    DegreeRequirementSetCreate,
    DegreeRequirementSetResponse,
)
from services.degree_plan.llm_course_breakdown import classify_course_breakdown


# -------------------------------------------------------------
# 1. Utility: Normalize course codes
# -------------------------------------------------------------
def normalize_code(c: str) -> str:
    if not c:
        return ""
    return c.replace(" ", "").upper().strip()


# Display-friendly normalization (keeps a space between subject/number)
def _normalize_course_code_display(code: Optional[str]) -> str:
    if not code:
        return ""
    cleaned = re.sub(r"\s+", " ", str(code)).strip().upper()
    if " " not in cleaned:
        cleaned = re.sub(r"([A-Z]+)(\d)", r"\1 \2", cleaned)
    return cleaned


def _normalize_catalog_year_display(catalog_year: Optional[str]) -> str:
    """Strip advisee-specific suffixes such as ::ADV-123 used for imported sets."""
    if not catalog_year:
        return ""
    value = str(catalog_year)
    if "::" in value:
        return value.split("::", 1)[0]
    return value


def normalize_catalog_display(catalog_year: Optional[str]) -> str:
    """Public helper imported by routes to keep catalog year tidy."""
    return _normalize_catalog_year_display(catalog_year)


def _infer_year_bucket(code: Optional[str]) -> str:
    """
    Roughly map a course code to a class year bucket based on leading digit.
    1xxx -> Freshman, 2xxx -> Sophomore, 3xxx -> Junior, 4xxx/5xxx -> Senior.
    """
    if not code:
        return "Other"
    digits = re.findall(r"\d+", code.replace(" ", ""))
    if not digits:
        return "Other"
    leading = digits[0][0]
    if leading == "1":
        return "Freshman"
    if leading == "2":
        return "Sophomore"
    if leading == "3":
        return "Junior"
    if leading in {"4", "5"}:
        return "Senior"
    return "Other"


def _course_detail(code: Optional[str], title: Optional[str] = None, credits: Optional[float] = None) -> Dict:
    """
    Build a consistent course detail payload used by the validator output.
    """
    display_code = _normalize_course_code_display(code)
    course_title = title or display_code
    detail = {
        "code": display_code,
        "title": course_title,
        "display": f"{display_code} - {course_title}" if course_title else display_code,
        "yearBucket": _infer_year_bucket(display_code),
    }
    if credits is not None:
        try:
            detail["credits"] = float(credits)
        except Exception:
            pass
    return detail


def _merge_completed_course_sources(*sources: List[Dict]) -> List[Dict]:
    """
    Merge multiple completed-course lists, deduplicating by code/term/title
    and skipping entries that are only planned.
    """
    merged: List[Dict] = []
    seen = set()

    for source in sources:
        for entry in source or []:
            status = str(entry.get("status") or "COMPLETED").upper()
            if status == "PLANNED":
                continue

            code_display = _normalize_course_code_display(entry.get("code"))
            if not code_display:
                continue

            term = entry.get("term")
            title = entry.get("title")
            key = (code_display, term or "", title or "")
            if key in seen:
                continue

            seen.add(key)
            try:
                credits_val = float(entry.get("credits") or 0)
            except Exception:
                credits_val = 0.0

            merged.append(
                {
                    "code": code_display,
                    "credits": credits_val,
                    "term": term,
                    "title": title,
                    "status": status,
                }
            )

    return merged


def _collect_assumed_corequisites(requirement_data: List[Dict]) -> set:
    """
    Some degree plans list placement-based co-requisites separately.
    Collect them so we can assume they are satisfied for prerequisite checks.
    """
    assumed = set()
    for group in requirement_data or []:
        co_req_map = group.get("co_requisites_if_placement_not_met")
        if not isinstance(co_req_map, dict):
            continue
        for codes in co_req_map.values():
            if not codes:
                continue
            for code in codes:
                if not code:
                    continue
                assumed.add(_normalize_course_code_display(code))
    return assumed


def _evaluate_course_prerequisites(course: Dict, completed: set) -> List[Dict]:
    """
    Return WARNING issues for unmet prerequisites. Corequisites and
    prereq-or-concurrent clauses are treated as satisfied.
    """
    warnings: List[Dict] = []
    completed_norm = {normalize_code(c) for c in (completed or set())}

    for clause in course.get("prerequisites", []) or []:
        clause_type = str(clause.get("type") or "PREREQUISITE").upper()
        if clause_type in {"COREQUISITE", "PREREQ_OR_CONCURRENT"}:
            continue

        raw_options = clause.get("options") or []
        required_codes = []
        for option in raw_options:
            for code in option or []:
                if code:
                    required_codes.append(code)

        display_codes = [_normalize_course_code_display(c) for c in required_codes]
        normalized_required = [normalize_code(c) for c in required_codes]

        clause_satisfied = all(code in completed_norm for code in normalized_required)
        if clause_satisfied:
            continue

        warnings.append(
            {
                "requirementId": course.get("code"),
                "message": clause.get("text")
                or "Prerequisite requirements are not satisfied",
                "missingCourses": sorted({c for c in display_codes if c}),
                "severity": "WARNING",
                "category": "PREREQUISITE",
            }
        )

    return warnings


def _build_general_education_summary(groups: List[Dict], completed: set):
    """
    Build a concise summary of general education progress.
    Returns tuple: (summary list, total required selections, satisfied selections)
    """
    summary: List[Dict] = []
    total_required = 0
    total_satisfied = 0
    completed_norm = {normalize_code(c) for c in (completed or set())}

    for group in groups or []:
        courses = group.get("courses") or []
        if not courses:
            continue

        required_selections = group.get("requiredSelections")
        if required_selections is None:
            required_selections = 2 if len(courses) >= 2 else len(courses)

        satisfied = 0
        taken_courses = []
        remaining_courses = []
        taken_course_details = []
        remaining_course_details = []

        for course in courses:
            code_display = _normalize_course_code_display(course.get("code"))
            title = course.get("title") or code_display
            display_value = f"{code_display} - {title}"

            if normalize_code(course.get("code")) in completed_norm:
                satisfied += 1
                taken_courses.append(display_value)
                taken_course_details.append(_course_detail(code_display, title, course.get("credits")))
            else:
                remaining_courses.append(display_value)
                remaining_course_details.append(_course_detail(code_display, title, course.get("credits")))

        satisfied = min(satisfied, required_selections)
        remaining = max(required_selections - satisfied, 0)

        total_required += required_selections
        total_satisfied += satisfied

        summary.append(
            {
                "groupId": group.get("id"),
                "title": group.get("title"),
                "description": group.get("description"),
                "requiredSelections": required_selections,
                "satisfiedSelections": satisfied,
                "remainingSelections": remaining,
                "takenCourses": taken_courses,
                "remainingCourses": remaining_courses,
                "takenCourseDetails": taken_course_details,
                "remainingCourseDetails": remaining_course_details,
            }
        )

    return summary, total_required, total_satisfied


def _categorize_requirement_groups(requirement_data: List[Dict]) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]:
    """
    Split requirement groups into general education, concentration, minor, and major buckets.
    Falls back to treating uncategorized groups as major requirements.
    """
    general_ed_types = {"category", "choose_one", "paired_group", "elective_pool", "credit_minimum"}
    general_ed_groups: List[Dict] = []
    concentration_groups: List[Dict] = []
    minor_groups: List[Dict] = []
    major_groups: List[Dict] = []

    for group in requirement_data or []:
        group_type = str(group.get("type") or "").lower()
        if group_type == "concentration":
            concentration_groups.append(group)
            continue
        if group_type == "minor":
            minor_groups.append(group)
            continue
        if group_type in general_ed_types or str(group.get("category") or "").lower() == "general_education":
            general_ed_groups.append(group)
            continue
        major_groups.append(group)

    return general_ed_groups, concentration_groups, minor_groups, major_groups


def _summarize_course_requirements(groups: List[Dict], completed_codes: set) -> Tuple[List[Dict], int, int, float, List[str]]:
    """
    Build summaries for major/minor style groups that list explicit courses.
    Returns:
      summaries, total_required_count, satisfied_count, completion_percent, needed_courses
    """
    summaries: List[Dict] = []
    total_required = 0
    total_satisfied = 0
    needed_courses: set = set()

    for group in groups or []:
        courses = group.get("courses") or []
        normalized = []

        for course in courses:
            code = course.get("code") if isinstance(course, dict) else course
            title = course.get("title") if isinstance(course, dict) else None
            credits = course.get("credits") if isinstance(course, dict) else None
            code_norm = normalize_code(code)
            code_display = _normalize_course_code_display(code)
            if not code_norm or not code_display:
                continue
            normalized.append((code_norm, code_display, title, credits))

        required_count = len(normalized)
        if required_count == 0:
            continue

        taken = [disp for norm, disp, _, _ in normalized if norm in completed_codes]
        missing = [disp for norm, disp, _, _ in normalized if norm not in completed_codes]

        taken_details = [
            _course_detail(disp, title, credits)
            for norm, disp, title, credits in normalized
            if norm in completed_codes
        ]
        missing_details = [
            _course_detail(disp, title, credits)
            for norm, disp, title, credits in normalized
            if norm not in completed_codes
        ]

        total_required += required_count
        total_satisfied += len(taken)
        needed_courses.update(missing)

        summaries.append(
            {
                "groupId": group.get("id"),
                "title": group.get("title") or group.get("id") or "Requirement",
                "requiredCount": required_count,
                "satisfiedCount": len(taken),
                "missingCourses": sorted(missing),
                "takenCourses": sorted(taken),
                "missingCourseDetails": missing_details,
                "takenCourseDetails": taken_details,
            }
        )

    completion_percent = (
        100.0 if total_required == 0 else round((total_satisfied / total_required) * 100, 2)
    )

    return summaries, total_required, total_satisfied, completion_percent, sorted(needed_courses)


# -------------------------------------------------------------
# 2. Identify concentration requirement groups
# -------------------------------------------------------------
def extract_concentration_groups(requirement_data: List[Dict]) -> List[Dict]:
    """Return all groups of type 'concentration'."""
    groups = []
    for g in requirement_data:
        if str(g.get("type", "")).lower() == "concentration":
            groups.append(g)
    return groups


# -------------------------------------------------------------
# 3. Compute course matches for one concentration
# -------------------------------------------------------------
def match_concentration(
    concentration: Dict,
    completed_codes: set
) -> Tuple[int, List[str], List[str]]:
    """
    Returns:
        match_count,
        taken_course_codes,
        missing_course_codes
    """

    required = [normalize_code(c["code"]) for c in concentration.get("requiredCourses", [])]
    choose = [normalize_code(c["code"]) for c in concentration.get("chooseCourses", [])]

    taken = []
    missing = []

    # Required courses
    for rc in required:
        if rc in completed_codes:
            taken.append(rc)
        else:
            missing.append(rc)

    # Choose-courses logic:
    # If concentration has chooseCourses, the hours requirement applies to required + choose bucket.
    hours_required = concentration.get("hoursRequired", 12)
    total_required_courses = len(required)

    # How many 3-hour courses equal to hours required?
    needed_count = math.ceil(hours_required / 3)

    # Already taken from required
    already_count = len(taken)

    # Remaining need from choose list
    remaining_needed = max(0, needed_count - already_count)

    # Evaluate choose courses
    choose_taken = [c for c in choose if c in completed_codes]
    choose_missing = [c for c in choose if c not in completed_codes]

    taken.extend(choose_taken)

    # Add missing choose-courses only if needed
    if remaining_needed > 0:
        # choose_missing list holds possible courses
        missing.extend(choose_missing)

    match_count = len(taken)

    return match_count, taken, missing


# -------------------------------------------------------------
# 4. Determine number of required concentrations for degree
# -------------------------------------------------------------
def required_concentration_count(program_code: str) -> int:
    """
    BBA-BUSINESS-ADMINISTRATION → 2 required concentrations
    All other programs → 1, if concentrations exist
    """
    program_code = program_code.upper().strip()
    if program_code == "BBA-BUSINESS-ADMINISTRATION":
        return 2
    return 1


# -------------------------------------------------------------
# 5. Choose strongest-matching concentrations
# -------------------------------------------------------------
def select_active_concentrations(
    concentration_groups: List[Dict],
    completed_codes: set,
    count_required: int
) -> List[Dict]:
    """
    Rank by # of matched courses. Pick top N.
    """
    scored = []

    for conc in concentration_groups:
        match_count, _, _ = match_concentration(conc, completed_codes)
        scored.append((match_count, conc))

    # Sort descending by match_count
    scored.sort(key=lambda x: x[0], reverse=True)

    # If degree has concentrations but student completed none, still pick top N
    active = [c for (_, c) in scored[:count_required]]

    return active


# -------------------------------------------------------------
# 6. Build validator output for concentrations
# -------------------------------------------------------------
def build_concentration_validation_output(
    active: List[Dict],
    completed_codes: set
) -> List[Dict]:
    """
    Construct validation-friendly summaries:
    [
      {
        "title": "Core Accounting Concepts",
        "hoursRequired": 12,
        "taken": [...],
        "needed": [...]
      },
      ...
    ]
    """

    results = []

    for conc in active:
        _, taken, missing = match_concentration(conc, completed_codes)

        results.append({
            "title": conc["title"],
            "hoursRequired": conc.get("hoursRequired", 12),
            "taken": sorted(taken),
            "needed": sorted(set(missing)),
        })

    return results


# -------------------------------------------------------------
# 7. MAIN VALIDATION SERVICE (patched)
# -------------------------------------------------------------
class DegreePlanService:
    """
    Provides CRUD helpers for requirement sets/contexts and performs
    lightweight validation used by the Degree Plan UI.
    """

    # ------------------------------------------------------------------
    # Requirement Set CRUD
    # ------------------------------------------------------------------
    @staticmethod
    def create_requirement_set(db: Session, payload: DegreeRequirementSetCreate):
        data = payload.model_dump()
        requirement_groups = data.pop("requirementGroups", [])

        requirement = DegreeRequirementSet(
            programCode=data["programCode"].strip(),
            catalogYear=data["catalogYear"].strip(),
            programName=data["programName"],
            totalCredits=data["totalCredits"],
            requirementData=requirement_groups,
            sourceDocument=data.get("sourceDocument"),
        )
        db.add(requirement)
        db.commit()
        db.refresh(requirement)
        return requirement

    @staticmethod
    def list_requirement_sets(db: Session, program_code: Optional[str] = None):
        query = db.query(DegreeRequirementSet)
        if program_code:
            query = query.filter(DegreeRequirementSet.programCode == program_code)
        results = query.order_by(DegreeRequirementSet.createdAt.desc()).all()
        serialized = []
        for req in results:
            payload = DegreePlanService._safe_requirement_set_response(req)
            if payload:
                serialized.append(payload)
        return serialized

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------
    @staticmethod
    def upsert_context(db: Session, advisee_id: int, payload: AdviseeContextUpsert):
        profile = db.query(AdviseeProfile).filter(AdviseeProfile.adviseeID == advisee_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Advisee profile not found")

        completed_courses = [
            course.model_dump() if hasattr(course, "model_dump") else course
            for course in payload.completedCourses or []
        ]

        requirement = (
            db.query(DegreeRequirementSet)
            .filter(DegreeRequirementSet.requirementSetID == payload.requirementSetID)
            .first()
        )
        if not requirement:
            raise HTTPException(status_code=404, detail="Requirement set not found")

        context = (
            db.query(AdviseeDegreeContext)
            .filter(AdviseeDegreeContext.adviseeID == advisee_id)
            .first()
        )

        if context:
            context.requirementSetID = payload.requirementSetID
            context.completedCourses = completed_courses
            context.overrides = payload.overrides
            context.notes = payload.notes
        else:
            context = AdviseeDegreeContext(
                adviseeID=advisee_id,
                requirementSetID=payload.requirementSetID,
                completedCourses=completed_courses,
                overrides=payload.overrides,
                notes=payload.notes,
            )
            db.add(context)

        db.commit()
        db.refresh(context)
        return context

    @staticmethod
    def _ensure_context(db: Session, advisee_id: int, allow_bootstrap: bool = True):
        profile = (
            db.query(AdviseeProfile)
            .filter(AdviseeProfile.adviseeID == advisee_id)
            .first()
        )
        if not profile:
            return None, None, None

        context = (
            db.query(AdviseeDegreeContext)
            .filter(AdviseeDegreeContext.adviseeID == advisee_id)
            .first()
        )

        requirement = context.requirementSet if context else None

        if not context and allow_bootstrap:
            requirement = (
                db.query(DegreeRequirementSet)
                .filter(DegreeRequirementSet.programCode == profile.major)
                .order_by(DegreeRequirementSet.updatedAt.desc())
                .first()
            )
            if requirement:
                context = AdviseeDegreeContext(
                    adviseeID=advisee_id,
                    requirementSetID=requirement.requirementSetID,
                    completedCourses=[],
                    notes="Auto-generated context",
                )
                db.add(context)
                db.commit()
                db.refresh(context)

        if not requirement and context:
            requirement = (
                db.query(DegreeRequirementSet)
                .filter(DegreeRequirementSet.requirementSetID == context.requirementSetID)
                .first()
            )

        return profile, context, requirement

    @staticmethod
    def _safe_requirement_set_response(requirement: Optional[DegreeRequirementSet]):
        if not requirement:
            return None

        normalized_catalog = normalize_catalog_display(requirement.catalogYear)

        try:
            payload = DegreeRequirementSetResponse.from_orm(requirement)
            payload.catalogYear = normalized_catalog
            return payload
        except ValidationError:
            pass  # Fall back to manual coercion for loosely-structured imports

        groups = []
        for group in requirement.requirementData or []:
            coerced = dict(group)

            # requiredCredits fallback
            required = (
                coerced.get("requiredCredits")
                or coerced.get("creditsRequired")
                or coerced.get("hoursRequired")
                or 0
            )
            try:
                coerced["requiredCredits"] = float(required)
            except Exception:
                coerced["requiredCredits"] = 0.0

            # Normalize courses list to satisfy schema
            courses = []
            for course in coerced.get("courses") or []:
                if not course:
                    continue
                if isinstance(course, dict):
                    code = _normalize_course_code_display(course.get("code"))
                    if not code:
                        continue
                    title = course.get("title") or code
                    credits = course.get("credits") or 0
                else:
                    code = _normalize_course_code_display(course)
                    if not code:
                        continue
                    title = code
                    credits = 0
                try:
                    credits_val = float(credits)
                except Exception:
                    credits_val = 0.0
                courses.append({"code": code, "title": title, "credits": credits_val})
            coerced["courses"] = courses

            groups.append(coerced)

        try:
            return DegreeRequirementSetResponse(
                requirementSetID=requirement.requirementSetID,
                programCode=requirement.programCode,
                catalogYear=normalized_catalog,
                programName=requirement.programName,
                totalCredits=requirement.totalCredits,
                requirementData=groups,
                sourceDocument=requirement.sourceDocument,
                createdAt=requirement.createdAt,
                updatedAt=requirement.updatedAt,
            )
        except ValidationError:
            return None

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_validation_record(record: DegreePlanValidation, extras: Optional[Dict] = None):
        if not record:
            return None

        payload = {
            "validationID": record.validationID,
            "adviseeID": record.adviseeID,
            "requirementSetID": record.requirementSetID,
            "status": record.status,
            "runType": record.runType,
            "completionPercent": float(record.completionPercent or 0.0),
            "issues": record.issues or [],
            "message": record.message,
            "triggeredBy": record.triggeredBy,
            "createdAt": record.createdAt,
            "updatedAt": record.updatedAt,
            "startedAt": record.startedAt,
            "finishedAt": record.finishedAt,
            "llmCourseBreakdown": record.llmCourseBreakdown,
            # Defaults for new UI fields
            "warnings": [],
            "concentrations": [],
            "minors": [],
            "concentrationIssues": [],
            "minorIssues": [],
            "concentrationRequirementCount": 0,
            "concentrationSatisfiedCount": 0,
            "concentrationCompletionPercent": 0.0,
            "minorRequirementCount": 0,
            "minorSatisfiedCount": 0,
            "minorCompletionPercent": 0.0,
            "generalEducation": [],
            "generalEducationRequirementCount": 0,
            "generalEducationSatisfiedCount": 0,
            "generalEducationCompletionPercent": 0.0,
            "majorRequirementCount": 0,
            "majorSatisfiedCount": 0,
            "majorCompletionPercent": 0.0,
            "majorRequirements": [],
            "minorRequirements": [],
            "majorNeededCourses": [],
            "minorNeededCourses": [],
            "outstandingRequirements": [],
        }

        extras = extras or {}
        # Extract warnings from issues if present
        if not extras.get("warnings") and payload["issues"]:
            payload["warnings"] = [
                issue for issue in payload["issues"] if str(issue.get("severity", "")).upper() == "WARNING"
            ]

        for key, value in extras.items():
            if value is not None:
                payload[key] = value

        return SimpleNamespace(**payload)

    @staticmethod
    def list_validations(db: Session, advisee_id: int):
        records = (
            db.query(DegreePlanValidation)
            .filter(DegreePlanValidation.adviseeID == advisee_id)
            .order_by(DegreePlanValidation.createdAt.desc())
            .all()
        )
        return [DegreePlanService._normalize_validation_record(rec) for rec in records]

    # ------------------------------------------------------------------
    # Summary endpoints
    # ------------------------------------------------------------------
    @staticmethod
    def get_advisee_summary(db: Session, advisee_id: int, allow_bootstrap: bool = True):
        from schemas.advisee import AdviseeResponse

        profile, context, requirement = DegreePlanService._ensure_context(db, advisee_id, allow_bootstrap)
        if not profile:
            raise HTTPException(status_code=404, detail="Advisee profile not found")

        requirement_payload = None
        if requirement:
            requirement_payload = DegreePlanService._safe_requirement_set_response(requirement)

        latest_validation = (
            db.query(DegreePlanValidation)
            .filter(DegreePlanValidation.adviseeID == advisee_id)
            .order_by(DegreePlanValidation.createdAt.desc())
            .first()
        )

        normalized_validation = None
        if latest_validation:
            computed_results = None
            try:
                computed_results = DegreePlanService.validate_degree_plan(db, advisee_id)
            except HTTPException:
                computed_results = None
            normalized_validation = DegreePlanService._normalize_validation_record(
                latest_validation,
                extras=computed_results,
            )

        student_payload = AdviseeResponse.from_orm(profile)

        return {
            "context": context,
            "requirementSet": requirement_payload,
            "latestValidation": normalized_validation,
            "student": student_payload,
            "transcript": None,
        }

    # ------------------------------------------------------------------
    # Validation core
    # ------------------------------------------------------------------
    @staticmethod
    def validate_degree_plan(db: Session, advisee_id: int) -> Dict:
        """
        Compute degree validation results including concentration and
        general-education summaries.
        """
        profile, context, requirement = DegreePlanService._ensure_context(
            db, advisee_id, allow_bootstrap=False
        )
        if not context:
            raise HTTPException(status_code=404, detail="Advisee context not found")
        if not requirement:
            raise HTTPException(status_code=404, detail="Requirement set not found")

        requirement_data = requirement.requirementData or []
        completed_courses = context.completedCourses or []

        completed_display = {_normalize_course_code_display(c.get("code")) for c in completed_courses}
        completed_codes = {normalize_code(code) for code in completed_display}

        (
            general_ed_groups,
            concentration_groups,
            minor_groups,
            major_groups,
        ) = _categorize_requirement_groups(requirement_data)

        # Fallback so legacy plans still show progress even if not categorized
        if not general_ed_groups:
            general_ed_groups = [
                g
                for g in requirement_data
                if g.get("courses")
                and str(g.get("type") or "").lower() not in {"concentration", "minor"}
            ]

        # General education summary
        general_summary, gen_required, gen_satisfied = _build_general_education_summary(
            general_ed_groups, completed_display
        )
        general_percent = 0.0 if gen_required == 0 else round((gen_satisfied / gen_required) * 100, 2)

        # Major/minor summaries
        major_summary, major_required, major_satisfied, major_percent, major_needed = _summarize_course_requirements(
            major_groups,
            completed_codes,
        )
        if major_required == 0:
            major_percent = 0.0

        minor_summary, minor_required, minor_satisfied, minor_percent, minor_needed = _summarize_course_requirements(
            minor_groups,
            completed_codes,
        )
        if minor_required == 0:
            minor_percent = 0.0

        # Concentration logic
        conc_required_count = (
            required_concentration_count(requirement.programCode or "")
            if concentration_groups
            else 0
        )
        active_concentrations = select_active_concentrations(
            concentration_groups, completed_codes, conc_required_count
        )

        concentration_summaries = []
        concentration_satisfied = 0
        for conc in active_concentrations:
            _, taken, missing = match_concentration(conc, completed_codes)
            required_hours = float(conc.get("hoursRequired", 12))
            completed_hours = float(len(taken) * 3)
            remaining_hours = max(required_hours - completed_hours, 0.0)
            courses_needed = max(len(conc.get("requiredCourses") or []), math.ceil(required_hours / 3))
            completed_course_count = min(len(taken), courses_needed)
            satisfied = completed_course_count >= courses_needed or remaining_hours <= 0.01
            if satisfied:
                concentration_satisfied += 1

            lookup: Dict[str, Dict] = {}
            for entry in conc.get("requiredCourses", []) + conc.get("chooseCourses", []):
                if not entry:
                    continue
                code_raw = entry.get("code") if isinstance(entry, dict) else entry
                code_norm = normalize_code(code_raw)
                if not code_norm:
                    continue
                lookup[code_norm] = entry if isinstance(entry, dict) else {"code": code_raw}

            missing_details = [
                _course_detail(
                    _normalize_course_code_display(code),
                    (lookup.get(code) or {}).get("title"),
                    (lookup.get(code) or {}).get("credits"),
                )
                for code in missing
            ]
            taken_details = [
                _course_detail(
                    _normalize_course_code_display(code),
                    (lookup.get(code) or {}).get("title"),
                    (lookup.get(code) or {}).get("credits"),
                )
                for code in taken
            ]

            concentration_summaries.append(
                {
                    "groupId": conc.get("id"),
                    "title": conc.get("title"),
                    "requiredSelections": 1,
                    "satisfiedSelections": 1 if satisfied else 0,
                    "requiredHours": required_hours,
                    "completedHours": completed_hours,
                    "remainingHours": remaining_hours,
                    "requiredCoursesCount": courses_needed,
                    "completedCoursesCount": completed_course_count,
                    "missingCourses": sorted({_normalize_course_code_display(c) for c in missing}),
                    "missingCourseDetails": missing_details,
                    "takenCourseDetails": taken_details,
                    "takenCourses": sorted({_normalize_course_code_display(c) for c in taken}),
                    "options": [
                        {
                            "name": conc.get("title") or conc.get("id") or "Concentration",
                            "requiredHours": required_hours,
                            "completedHours": completed_hours,
                            "remainingHours": remaining_hours,
                            "satisfied": satisfied,
                            "takenCourses": sorted({_normalize_course_code_display(c) for c in taken}),
                            "missingCourses": sorted({_normalize_course_code_display(c) for c in missing}),
                            "missingCourseDetails": missing_details,
                            "takenCourseDetails": taken_details,
                        }
                    ],
                }
            )

        concentration_percent = (
            100.0
            if conc_required_count == 0
            else round((concentration_satisfied / conc_required_count) * 100, 2)
        )

        # Prerequisite warnings
        assumed_coreqs = _collect_assumed_corequisites(requirement_data)
        prereq_warnings: List[Dict] = []
        for group in requirement_data or []:
            for course in group.get("courses") or []:
                prereq_warnings.extend(
                    _evaluate_course_prerequisites(
                        course,
                        completed_display | assumed_coreqs,
                    )
            )

        completion_components = []
        if gen_required:
            completion_components.append(general_percent)
        if major_required:
            completion_components.append(major_percent)
        if conc_required_count:
            completion_components.append(concentration_percent)
        if minor_required:
            completion_components.append(minor_percent)

        completion_percent = (
            round(sum(completion_components) / len(completion_components), 2)
            if completion_components
            else 0.0
        )

        outstanding_requirements: List[Dict] = []

        def _append_outstanding(payload: Dict):
            required_count = payload.get("requiredCount") or 0
            satisfied_count = payload.get("satisfiedCount") or 0
            if required_count <= 0:
                return
            if satisfied_count >= required_count:
                return
            outstanding_requirements.append(payload)

        # General education gaps
        for group in general_summary:
            if (group.get("remainingSelections") or 0) <= 0:
                continue

            required_count = group.get("requiredSelections") or 0
            satisfied_count = group.get("satisfiedSelections") or 0
            remaining_details = group.get("remainingCourseDetails") or [
                _course_detail(item.split(" - ")[0], item.split(" - ", 1)[1] if " - " in item else None)
                for item in group.get("remainingCourses") or []
            ]

            _append_outstanding(
                {
                    "requirementId": group.get("groupId") or group.get("title"),
                    "title": group.get("title") or "General Education Requirement",
                    "category": "generalEducation",
                    "message": group.get("description"),
                    "requiredCount": required_count,
                    "satisfiedCount": satisfied_count,
                    "completionPercent": 0.0 if required_count == 0 else round((satisfied_count / required_count) * 100, 2),
                    "missingCourses": remaining_details,
                }
            )

        # Major requirement gaps
        for item in major_summary:
            missing_details = item.get("missingCourseDetails") or [_course_detail(c) for c in item.get("missingCourses", [])]
            _append_outstanding(
                {
                    "requirementId": item.get("groupId") or item.get("title"),
                    "title": item.get("title") or "Major Requirement",
                    "category": "major",
                    "requiredCount": item.get("requiredCount") or 0,
                    "satisfiedCount": item.get("satisfiedCount") or 0,
                    "completionPercent": (
                        0.0
                        if not item.get("requiredCount")
                        else round((item.get("satisfiedCount") or 0) / item.get("requiredCount") * 100, 2)
                    ),
                    "missingCourses": missing_details,
                }
            )

        # Minor requirement gaps
        for item in minor_summary:
            missing_details = item.get("missingCourseDetails") or [_course_detail(c) for c in item.get("missingCourses", [])]
            _append_outstanding(
                {
                    "requirementId": item.get("groupId") or item.get("title"),
                    "title": item.get("title") or "Minor Requirement",
                    "category": "minor",
                    "requiredCount": item.get("requiredCount") or 0,
                    "satisfiedCount": item.get("satisfiedCount") or 0,
                    "completionPercent": (
                        0.0
                        if not item.get("requiredCount")
                        else round((item.get("satisfiedCount") or 0) / item.get("requiredCount") * 100, 2)
                    ),
                    "missingCourses": missing_details,
                }
            )

        # Concentration gaps
        for conc in concentration_summaries:
            missing_details = conc.get("missingCourseDetails") or conc.get("options", [{}])[0].get("missingCourseDetails") or []
            _append_outstanding(
                {
                    "requirementId": conc.get("groupId") or conc.get("title"),
                    "title": conc.get("title") or "Concentration Requirement",
                    "category": "concentration",
                    "requiredCount": conc.get("requiredCoursesCount") or conc.get("requiredSelections") or 0,
                    "satisfiedCount": conc.get("completedCoursesCount") or conc.get("satisfiedSelections") or 0,
                    "completionPercent": (
                        0.0
                        if not (conc.get("requiredCoursesCount") or conc.get("requiredSelections"))
                        else round(
                            (conc.get("completedCoursesCount") or conc.get("satisfiedSelections") or 0)
                            / (conc.get("requiredCoursesCount") or conc.get("requiredSelections"))
                            * 100,
                            2,
                        )
                    ),
                    "missingCourses": missing_details,
                }
            )

        llm_breakdown = classify_course_breakdown(
            requirement_set=requirement,
            completed_courses=completed_courses,
            validation_result={
                "groupResults": [],
                "concentrations": concentration_summaries,
                "minors": minor_summary,
                "majorRequirements": major_summary,
            },
        )

        return {
            "contextID": context.contextID,
            "requirementSetID": requirement.requirementSetID,
            "programCode": requirement.programCode,
            "issues": [],
            "warnings": prereq_warnings,
            "generalEducation": general_summary,
            "generalEducationRequirementCount": gen_required,
            "generalEducationSatisfiedCount": gen_satisfied,
            "generalEducationCompletionPercent": general_percent,
            "majorRequirements": major_summary,
            "majorRequirementCount": major_required,
            "majorSatisfiedCount": major_satisfied,
            "majorCompletionPercent": major_percent,
            "majorNeededCourses": major_needed,
            "concentrations": concentration_summaries,
            "concentrationRequirementCount": conc_required_count,
            "concentrationSatisfiedCount": concentration_satisfied,
            "concentrationCompletionPercent": concentration_percent,
            "minorRequirementCount": minor_required,
            "minorSatisfiedCount": minor_satisfied,
            "minorCompletionPercent": minor_percent,
            "minorRequirements": minor_summary,
            "minorNeededCourses": minor_needed,
            "minors": [],
            "outstandingRequirements": outstanding_requirements,
            "llmCourseBreakdown": llm_breakdown,
            "completionPercent": completion_percent,
            "completed": sorted(completed_codes),
        }

    @staticmethod
    def _run_validation(db: Session, advisee_id: int, validation: DegreePlanValidation):
        validation.status = ValidationStatus.RUNNING
        validation.startedAt = datetime.utcnow()
        db.commit()

        try:
            results = DegreePlanService.validate_degree_plan(db, advisee_id)

            validation.requirementSetID = results.get("requirementSetID")
            validation.contextID = results.get("contextID")
            validation.completionPercent = results.get("completionPercent", 0.0)
            validation.issues = results.get("issues", [])
            validation.llmCourseBreakdown = results.get("llmCourseBreakdown")

            status_value = ValidationStatus.PASSED
            for issue in results.get("issues", []):
                severity = str(issue.get("severity", "")).upper()
                if severity == "ERROR":
                    status_value = ValidationStatus.FAILED
                    break

            validation.status = status_value
            validation.finishedAt = datetime.utcnow()

            extras = {k: v for k, v in results.items() if k not in {"issues"}}
            db.commit()

            return DegreePlanService._normalize_validation_record(validation, extras=extras)
        except Exception as exc:  # pragma: no cover - defensive
            validation.status = ValidationStatus.ERROR
            validation.message = str(exc)
            validation.finishedAt = datetime.utcnow()
            db.commit()
            return DegreePlanService._normalize_validation_record(validation)

    @staticmethod
    def _execute_validation(advisee_id: int, validation_id: int):
        db = SessionLocal()
        try:
            validation = db.query(DegreePlanValidation).get(validation_id)
            if not validation:
                return
            DegreePlanService._run_validation(db, advisee_id, validation)
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Enqueue validation run
    # ------------------------------------------------------------------
    @staticmethod
    def enqueue_validation(
        db: Session,
        advisee_id: int,
        run_type: ValidationRunType = ValidationRunType.MANUAL,
        triggered_by: Optional[int] = None,
        background_tasks: Optional[BackgroundTasks] = None,
    ):
        validation = DegreePlanValidation(
            adviseeID=advisee_id,
            runType=run_type,
            status=ValidationStatus.PENDING,
            triggeredBy=triggered_by,
        )
        db.add(validation)
        db.commit()
        db.refresh(validation)

        if background_tasks:
            background_tasks.add_task(
                DegreePlanService._execute_validation,
                advisee_id,
                validation.validationID,
            )
            normalized = DegreePlanService._normalize_validation_record(validation)
        else:
            normalized = DegreePlanService._run_validation(db, advisee_id, validation)

        return normalized
