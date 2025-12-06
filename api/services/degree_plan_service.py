import logging
import math
import os
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote_plus

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import case
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from db.database import SessionLocal
from models.advisee import AdviseeProfile
from models.degree_plan import (
    AdviseeDegreeContext,
    DegreePlanValidation,
    DegreeRequirementSet,
    ValidationRunType,
    ValidationStatus,
)
from models.schedule import (
    Schedule,
    Class,
    Section,
    Course,
    ScheduleStatusEnum,
)
from schemas.degree_plan import (
    AdviseeContextUpsert,
    DegreeRequirementSetCreate,
    DegreeRequirementSetResponse,
)
from services.category_rules import (
    CATEGORY_RULES,
    detect_category_from_group,
    detect_category_from_courses,
    completed_satisfies_category,
)
from services.course_matching import (
    extract_codes_from_text,
    expand_requirement_codes,
    merge_completed_sources,
    serialize_courses,
)
from services.degree_importer import import_degree_plan_from_pdf_url
from services.transcript_service import TranscriptService


CATALOG_SEARCH_URL = os.environ.get(
    "DEGREE_PLAN_CATALOG_SEARCH_URL",
    "https://uafs.edu/search?q={query}",
)
DEFAULT_CATALOG_YEAR = os.environ.get("DEGREE_PLAN_DEFAULT_CATALOG_YEAR", "2024-2025")

CATALOG_YEAR_PATTERN = re.compile(r"(20\d{2})(?:[-/](20\d{2}))?")


# ------------------------------
# UTILITIES
# ------------------------------

def normalize_catalog_display(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    marker = "::ADV-"
    return value.split(marker, 1)[0].strip() if marker in value else value


def _normalize_catalog_year_display(value: Optional[str]) -> Optional[str]:
    """
    Backwards-compatible alias used in existing unit tests.
    """
    return normalize_catalog_display(value)


def _merge_completed_course_sources(*sources: Optional[List[dict]]):
    """
    Backwards-compatible alias that points to the shared merge helper.
    """
    return merge_completed_sources(*sources)


def load_context(db: Session, advisee_id: int) -> Optional[AdviseeDegreeContext]:
    return (
        db.query(AdviseeDegreeContext)
        .filter(AdviseeDegreeContext.adviseeID == advisee_id)
        .first()
    )


# ------------------------------
# DEGREE PLAN SERVICE
# ------------------------------

class DegreePlanService:

    # ----------------------------------------
    # CONTEXT LOADING & BOOTSTRAP
    # ----------------------------------------
    @staticmethod
    def _normalize_validation_record(record: Optional[DegreePlanValidation]):
        if record:
            record.issues = record.issues or []
            if record.completionPercent is None:
                record.completionPercent = 0.0
        return record

    @staticmethod
    def _is_manual_requirement(requirement: Optional[DegreeRequirementSet], advisee_id: int) -> bool:
        if not requirement:
            return False
        scope = f"advisee:{advisee_id}"
        suffix = f"::ADV-{advisee_id}"
        source = (requirement.sourceDocument or "").strip()
        catalog = (requirement.catalogYear or "").strip()
        return bool(source == scope or catalog.endswith(suffix))

    @classmethod
    def _load_manual_requirement(cls, db: Session, advisee_id: int) -> Optional[DegreeRequirementSet]:
        scope = f"advisee:{advisee_id}"
        suffix = f"::ADV-{advisee_id}"
        requirement = (
            db.query(DegreeRequirementSet)
            .filter(DegreeRequirementSet.sourceDocument == scope)
            .order_by(DegreeRequirementSet.updatedAt.desc())
            .first()
        )
        if requirement:
            return requirement
        return (
            db.query(DegreeRequirementSet)
            .filter(DegreeRequirementSet.catalogYear.ilike(f"%{suffix}"))
            .order_by(DegreeRequirementSet.updatedAt.desc())
            .first()
        )

    @staticmethod
    def _normalize_program_code(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        v = value.replace(" ", "-").strip().upper()
        return v or None

    @staticmethod
    def _infer_catalog_year(profile: AdviseeProfile) -> str:
        raw = (profile.degree_plan or "").strip()
        if not raw:
            return DEFAULT_CATALOG_YEAR

        m = CATALOG_YEAR_PATTERN.search(raw)
        if m:
            start, end = m.group(1), m.group(2)
            return f"{start}-{end}" if end else start

        up = raw.upper()
        if up.startswith("CAT"):
            return up

        return DEFAULT_CATALOG_YEAR

    @staticmethod
    def _build_keywords(*terms: Optional[str]) -> List[str]:
        keywords = []
        for t in terms:
            if not t:
                continue
            tokens = re.split(r"[\s,/._-]+", t)
            keywords.extend(tok for tok in tokens if tok)
        return keywords

    @staticmethod
    def _build_catalog_seed_url(program_code: Optional[str], catalog_year: Optional[str]):
        terms = [program_code or "", catalog_year or "", "degree plan pdf"]
        query = "+".join(quote_plus(t.strip()) for t in terms if t and t.strip())

        if "{query}" in CATALOG_SEARCH_URL:
            return CATALOG_SEARCH_URL.format(query=query or "degree+plan")

        suffix = "" if CATALOG_SEARCH_URL.endswith(("?", "&")) else (
            "&" if "?" in CATALOG_SEARCH_URL else "?"
        )
        return f"{CATALOG_SEARCH_URL}{suffix}{query}"

    @classmethod
    def _bootstrap_context(cls, db: Session, advisee_id: int):
        profile = (
            db.query(AdviseeProfile)
            .filter(AdviseeProfile.adviseeID == advisee_id)
            .first()
        )
        if not profile:
            return False

        program_hint = (profile.degree_plan or "").strip()
        major_code = (profile.major or "").strip()
        if not (program_hint or major_code):
            return False

        catalog_year = cls._infer_catalog_year(profile)
        keywords = cls._build_keywords(program_hint, major_code, catalog_year)
        seed_url = cls._build_catalog_seed_url(program_hint or major_code, catalog_year)

        try:
            import_degree_plan_from_pdf_url(
                db,
                advisee_id,
                pdf_url=seed_url,
                required_keywords=keywords,
                create_validation=False,
            )
            return True
        except Exception as exc:
            logging.warning(
                "Degree plan bootstrap failed for advisee %s: %s",
                advisee_id,
                exc,
            )
            return False

    @classmethod
    def _ensure_context(cls, db: Session, advisee_id: int):
        profile = (
            db.query(AdviseeProfile)
            .filter(AdviseeProfile.adviseeID == advisee_id)
            .first()
        )
        context = load_context(db, advisee_id)

        requirement = (
            db.query(DegreeRequirementSet)
            .filter(
                DegreeRequirementSet.requirementSetID == context.requirementSetID
            )
            .first()
            if context else None
        )

        desired_code = cls._normalize_program_code(
            (profile.degree_plan or profile.major) if profile else None
        )
        requirement_code = cls._normalize_program_code(
            requirement.programCode if requirement else None
        )
        manual_requirement = requirement if cls._is_manual_requirement(requirement, advisee_id) else None
        if not manual_requirement:
            manual_requirement = cls._load_manual_requirement(db, advisee_id)

        if not context and manual_requirement:
            context = AdviseeDegreeContext(
                adviseeID=advisee_id,
                requirementSetID=manual_requirement.requirementSetID,
                completedCourses=[],
            )
            db.add(context)
            db.commit()
            db.refresh(context)
            requirement = manual_requirement
            requirement_code = cls._normalize_program_code(manual_requirement.programCode)

        needs_bootstrap = (
            not manual_requirement
            and (
                not context
                or not requirement
                or (desired_code and requirement_code and desired_code != requirement_code)
            )
        )

        if needs_bootstrap:
            if cls._bootstrap_context(db, advisee_id):
                context = load_context(db, advisee_id)
                if context:
                    requirement = (
                        db.query(DegreeRequirementSet)
                        .filter(
                            DegreeRequirementSet.requirementSetID == context.requirementSetID
                        )
                        .first()
                    )
                    if cls._is_manual_requirement(requirement, advisee_id):
                        manual_requirement = requirement

        return profile, context, requirement

    # ----------------------------------------
    # COURSE COLLECTION
    # ----------------------------------------
    @staticmethod
    def _collect_courses_from_schedules(db: Session, advisee_id: int):
        schedules = (
            db.query(Schedule)
            .options(
                joinedload(Schedule.term),
                joinedload(Schedule.classes)
                .joinedload(Class.section)
                .joinedload(Section.course),
            )
            .filter(Schedule.adviseeID == advisee_id)
            .order_by(
                case(
                    (Schedule.status == ScheduleStatusEnum.APPROVED, 0),
                    else_=1
                ),
                Schedule.createdWhen.desc(),
            )
            .all()
        )

        result = []
        seen_sections = set()

        for sched in schedules:
            term_label = sched.term.code if sched.term else None
            is_completed = (
                sched.status.value == ScheduleStatusEnum.APPROVED.value
            )
            status = "COMPLETED" if is_completed else "PLANNED"

            for cls in sched.classes:
                if cls.sectionID in seen_sections:
                    continue
                seen_sections.add(cls.sectionID)

                section = cls.section
                course = section.course if section else None

                code = ""
                if course and course.courseName:
                    code = course.courseName.strip()
                elif section and section.crn:
                    code = str(section.crn)

                title = course.courseName if course else None
                if course and course.description:
                    title = course.description
                elif not title and section and section.description:
                    title = section.description

                credits = 0
                if course and course.credits:
                    try:
                        credits = float(course.credits)
                    except:
                        credits = 0
                if credits <= 0:
                    credits = 3.0

                result.append({
                    "code": code or f"CLASS-{cls.classID}",
                    "title": title,
                    "credits": credits,
                    "term": term_label,
                    "status": status,
                })

        return serialize_courses(result)

    @staticmethod
    def _collect_courses_from_transcript(db: Session, advisee_id: int):
        enrollments = TranscriptService._load_enrollments(db, advisee_id)
        if not enrollments:
            return []

        terms = TranscriptService._build_terms(enrollments)
        completed = []

        for term in terms:
            for c in term.courses:
                if (c.status or "").lower() != "completed":
                    continue

                code_candidates = extract_codes_from_text(
                    " ".join(x for x in [
                        getattr(c, "courseCode", None),
                        getattr(c, "courseTitle", None),
                    ] if x)
                )

                normalized = next(iter(sorted(code_candidates)), None)
                if not normalized:
                    normalized = (getattr(c, "courseCode", "") or "").upper()

                completed.append({
                    "code": normalized,
                    "title": getattr(c, "courseTitle", None),
                    "credits": float(c.credits or 0),
                    "term": term.term,
                    "status": "COMPLETED",
                })

        return completed

    # ----------------------------------------
    # CONTEXT / REQUIREMENT SET API
    # ----------------------------------------
    @staticmethod
    def create_requirement_set(db: Session, payload: DegreeRequirementSetCreate):
        groups = [g.dict() for g in payload.requirementGroups]
        record = DegreeRequirementSet(
            programCode=payload.programCode,
            catalogYear=payload.catalogYear,
            programName=payload.programName,
            totalCredits=payload.totalCredits,
            requirementData=groups,
            sourceDocument=payload.sourceDocument,
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = (
                db.query(DegreeRequirementSet)
                .filter(
                    DegreeRequirementSet.programCode == payload.programCode,
                    DegreeRequirementSet.catalogYear == payload.catalogYear,
                )
                .first()
            )
            if existing:
                return existing
            raise

        db.refresh(record)
        return record

    @staticmethod
    def list_requirement_sets(db: Session, program_code: Optional[str] = None):
        query = db.query(DegreeRequirementSet)
        if program_code:
            normalized = DegreePlanService._normalize_program_code(program_code)
            if normalized:
                query = query.filter(DegreeRequirementSet.programCode == normalized)
        return query.order_by(DegreeRequirementSet.updatedAt.desc()).all()

    @staticmethod
    def upsert_context(db: Session, advisee_id: int, payload: AdviseeContextUpsert):
        requirement = (
            db.query(DegreeRequirementSet)
            .filter(DegreeRequirementSet.requirementSetID == payload.requirementSetID)
            .first()
        )
        if not requirement:
            raise HTTPException(404, "Requirement set not found")

        context = load_context(db, advisee_id)
        if not context:
            context = AdviseeDegreeContext(
                adviseeID=advisee_id,
                requirementSetID=requirement.requirementSetID,
            )
            db.add(context)

        context.requirementSetID = requirement.requirementSetID
        context.completedCourses = serialize_courses(
            [c.dict() for c in payload.completedCourses]
        )
        context.overrides = payload.overrides
        context.notes = payload.notes

        db.commit()
        db.refresh(context)
        return context

    # ----------------------------------------
    # SUMMARY
    # ----------------------------------------
    @staticmethod
    def get_advisee_summary(db: Session, advisee_id: int):
        profile, context, requirement = DegreePlanService._ensure_context(db, advisee_id)
        student_payload = profile
        transcript_payload = None

        if profile:
            try:
                transcript_payload = TranscriptService.get_transcript_for_advisee(
                    db,
                    advisee_id,
                    {"role": "advisor"},
                )
            except HTTPException as exc:
                if exc.status_code != 404:
                    logging.warning(
                        "Failed to load transcript for advisee %s: %s",
                        advisee_id,
                        exc.detail if hasattr(exc, "detail") else exc,
                    )

        latest_validation = (
            db.query(DegreePlanValidation)
            .filter(DegreePlanValidation.adviseeID == advisee_id)
            .order_by(DegreePlanValidation.createdAt.desc())
            .first()
        )
        latest_validation = DegreePlanService._normalize_validation_record(latest_validation)

        transcript_courses = DegreePlanService._collect_courses_from_transcript(db, advisee_id)
        schedule_courses = DegreePlanService._collect_courses_from_schedules(db, advisee_id)

        completed_courses = (
            transcript_courses if transcript_courses else schedule_courses
        )

        if context and completed_courses:
            context.completedCourses = completed_courses

        requirement_payload = None
        if requirement:
            requirement_payload = DegreeRequirementSetResponse(
                requirementSetID=requirement.requirementSetID,
                programCode=(profile.major if profile else None) or requirement.programCode,
                catalogYear=normalize_catalog_display(requirement.catalogYear),
                programName=(
                    profile.degree_plan
                    if profile and profile.degree_plan
                    else requirement.programName
                ),
                totalCredits=requirement.totalCredits,
                requirementGroups=requirement.requirementData or [],
                sourceDocument=requirement.sourceDocument,
                createdAt=requirement.createdAt,
                updatedAt=requirement.updatedAt,
            )

        return {
            "context": context,
            "requirementSet": requirement_payload,
            "latestValidation": latest_validation,
            "student": student_payload,
            "transcript": transcript_payload,
        }

    # ----------------------------------------
    # VALIDATION MANAGEMENT
    # ----------------------------------------
    @staticmethod
    def list_validations(db: Session, advisee_id: int):
        records = (
            db.query(DegreePlanValidation)
            .filter(DegreePlanValidation.adviseeID == advisee_id)
            .order_by(DegreePlanValidation.createdAt.desc())
            .all()
        )
        return [
            DegreePlanService._normalize_validation_record(record)
            for record in records
        ]

    @classmethod
    def enqueue_validation(
        cls,
        db: Session,
        advisee_id: int,
        run_type: ValidationRunType = ValidationRunType.MANUAL,
        triggered_by: Optional[int] = None,
        background_tasks: Optional[BackgroundTasks] = None,
    ):
        _, context, requirement = cls._ensure_context(db, advisee_id)

        if not context or not requirement:
            raise HTTPException(404, "No degree plan context is linked to this advisee")

        normalized_run_type = (
            run_type if isinstance(run_type, ValidationRunType) else ValidationRunType(run_type)
        )

        validation = DegreePlanValidation(
            adviseeID=advisee_id,
            contextID=context.contextID,
            requirementSetID=requirement.requirementSetID,
            status=ValidationStatus.PENDING,
            runType=normalized_run_type,
            triggeredBy=triggered_by,
        )

        db.add(validation)
        db.commit()
        db.refresh(validation)
        validation = cls._normalize_validation_record(validation)

        if background_tasks:
            background_tasks.add_task(process_validation_job, validation.validationID)
        else:
            process_validation_job(validation.validationID)

        return validation

    # ----------------------------------------
    # VALIDATION CORE
    # ----------------------------------------
    @staticmethod
    def _process_validation(db: Session, validation_id: int):
        validation = (
            db.query(DegreePlanValidation)
            .filter(DegreePlanValidation.validationID == validation_id)
            .first()
        )
        if not validation:
            return

        validation.status = ValidationStatus.RUNNING
        validation.startedAt = datetime.utcnow()
        db.commit()

        context = validation.context
        requirement = validation.requirementSet

        if not context or not requirement:
            validation.status = ValidationStatus.ERROR
            validation.message = "Missing requirement data"
            validation.finishedAt = datetime.utcnow()
            validation.issues = []
            db.commit()
            return

        # --- Collect completed courses ---
        transcript = DegreePlanService._collect_courses_from_transcript(db, validation.adviseeID)
        context_courses = context.completedCourses or []
        completed_courses = merge_completed_sources(transcript, context_courses)
        context.completedCourses = completed_courses

        completed_codes = {
            (c.get("code") or "").upper().strip()
            for c in completed_courses
        }

        groups = requirement.requirementData or []
        issues = []
        total_items = 0
        satisfied_items = 0

        # ----------------------------------------
        # Validate each requirement group
        # ----------------------------------------
        for group in groups:
            title = group.get("title", "")
            description = group.get("description", "")
            group_courses = group.get("courses", [])
            group_id = group.get("id") or title

            # DETECT CATEGORY REQUIREMENT
            category = detect_category_from_group(title, description)
            if not category:
                category = detect_category_from_courses(group_courses, category)

            # ----------------------------------------
            # CATEGORY MODE
            # ----------------------------------------
            if category:
                total_items += 1
                satisfied = completed_satisfies_category(category, completed_courses)

                # If any of the explicitly listed courses satisfy it
                if not satisfied:
                    acceptable_codes = set()
                    for c in group_courses:
                        acceptable_codes |= expand_requirement_codes(c or {}, description)
                    if acceptable_codes & completed_codes:
                        satisfied = True

                if satisfied:
                    satisfied_items += 1
                    continue

                label = CATEGORY_RULES[category]["label"]
                issues.append({
                    "requirementId": group_id,
                    "message": f"Missing: {label}",
                    "missingCourses": [label],
                })
                continue

            # ----------------------------------------
            # SPECIFIC COURSE MODE
            # ----------------------------------------
            required_credits = 0.0
            try:
                required_credits = float(group.get("requiredCredits") or 0)
            except:
                required_credits = 0.0

            missing_entries = []
            group_total_credits = 0.0
            satisfied_credits = 0.0
            entries_count = 0
            satisfied_count = 0
            used_codes = set()

            # Collect requirement entries
            for course in group_courses:
                expanded = expand_requirement_codes(course, description)
                if not expanded:
                    continue  # optional descriptor-only course

                entries_count += 1

                credit = 0.0
                try:
                    credit = float(course.get("credits") or 0)
                except:
                    credit = 0.0
                if credit <= 0:
                    credit = 3.0

                group_total_credits += credit

                matched = next((code for code in expanded if code in completed_codes), None)

                if matched:
                    if matched not in used_codes:
                        used_codes.add(matched)
                        satisfied_credits += credit
                        satisfied_count += 1
                    continue

                missing_entries.append("/".join(sorted(expanded)))

            # Determine if credit-based choice group
            is_choice = (
                required_credits > 0
                and group_total_credits > required_credits + 0.01
            )

            if is_choice:
                avg_credit = group_total_credits / entries_count if entries_count else 0
                if avg_credit <= 0:
                    avg_credit = 3.0

                needed = max(1, math.ceil(required_credits / avg_credit))
                needed = min(needed, entries_count)

                total_items += needed
                satisfied_items += min(satisfied_count, needed)

                if satisfied_credits < required_credits:
                    remain = max(0, round(required_credits - satisfied_credits, 2))
                    issues.append({
                        "requirementId": group_id,
                        "message": f"Need {remain:g} more credit(s) from {title}",
                        "missingCourses": [
                            f"{title}: additional {remain:g} credit(s) needed"
                        ],
                    })
                continue

            # Normal required-course list mode
            total_items += entries_count
            satisfied_items += satisfied_count

            if missing_entries:
                issues.append({
                    "requirementId": group_id,
                    "message": f"Missing {len(missing_entries)} requirement(s) in {title}",
                    "missingCourses": missing_entries,
                })

        # ----------------------------------------
        # COMPLETION %
        # ----------------------------------------
        if total_items > 0:
            completion = round((satisfied_items / total_items) * 100, 2)
        else:
            completion = 0.0

        validation.completionPercent = completion
        validation.issues = issues
        validation.status = ValidationStatus.PASSED if not issues else ValidationStatus.FAILED
        validation.message = (
            "All requirements satisfied." if not issues else "Outstanding requirements."
        )
        validation.finishedAt = datetime.utcnow()

        db.commit()
        db.refresh(validation)


# ----------------------------------------
# JOB WRAPPER
# ----------------------------------------
def process_validation_job(validation_id: int):
    db = SessionLocal()
    try:
        DegreePlanService._process_validation(db, validation_id)
    finally:
        db.close()
