import logging
import os
import re
from datetime import datetime
from typing import List, Optional, Set, Tuple
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
    ValidationIssue,
)
from services.degree_importer import import_degree_plan_from_pdf_url
from services.transcript_service import TranscriptService

CATALOG_SEARCH_URL = os.environ.get(
    "DEGREE_PLAN_CATALOG_SEARCH_URL",
    "https://uafs.edu/search?q={query}",
)
DEFAULT_CATALOG_YEAR = os.environ.get("DEGREE_PLAN_DEFAULT_CATALOG_YEAR", "2024-2025")
CATALOG_YEAR_PATTERN = re.compile(r"(20\d{2})(?:[-/](20\d{2}))?")
COURSE_CODE_PATTERN = re.compile(r"\b([A-Z]{2,4})\s*-?\s*(\d{3,4}[A-Z]?)\b")

LAB_SCIENCE_PREFIXES = {
    "ASTR",
    "BIOL",
    "CHEM",
    "GEOG",
    "GEOL",
    "GEOS",
    "PHSC",
    "PHYS",
}
FINE_ARTS_PREFIXES = {
    "ART",
    "ARTH",
    "DANC",
    "FILM",
    "MUS",
    "THEA",
}

REQUIREMENT_CATEGORY_RULES = {
    "lab_science": {
        "label": "Lab Science Requirement",
        "requirement_keywords": {
            "LAB SCIENCE",
            "SCIENCE LAB",
            "LABORATORY SCIENCE",
            "SCIENCE W/LAB",
            "SCIENCE W-LAB",
        },
        "course_prefixes": LAB_SCIENCE_PREFIXES,
        "course_keywords": {
            "BIOLOGY",
            "CHEMISTRY",
            "PHYSICS",
            "GEOLOGY",
            "ASTRONOMY",
            "LAB SCIENCE",
        },
    },
    "fine_arts": {
        "label": "Fine Arts Requirement",
        "requirement_keywords": {
            "FINE ART",
            "FINE-ART",
            "FINE ARTS",
            "ARTS REQUIREMENT",
            "CREATIVE ARTS",
            "ART/MUSIC",
            "ART OR MUSIC",
            "ART OR THEATRE",
        },
        "course_prefixes": FINE_ARTS_PREFIXES,
        "course_keywords": {
            "FINE ART",
            "MUSIC",
            "THEATRE",
            "THEATER",
            "DANCE",
            "ART HISTORY",
            "ART APPRECIATION",
        },
    },
}


def _serialize_completed_courses(courses: List[dict]) -> List[dict]:
    serialized = []
    for course in courses or []:
        serialized.append(
            {
                "code": course.get("code", "").upper(),
                "title": course.get("title"),
                "credits": float(course.get("credits", 0)),
                "term": course.get("term"),
                "status": course.get("status", "COMPLETED"),
            }
        )
    return serialized


def _normalize_validation(validation: Optional[DegreePlanValidation]):
    if validation and validation.issues is None:
        validation.issues = []
    return validation

def _extract_codes_from_text(value: Optional[str]) -> Set[str]:
    if not value:
        return set()
    matches = COURSE_CODE_PATTERN.findall(value.upper())
    normalized = set()
    for prefix, number in matches:
        if not prefix or not number:
            continue
        normalized.add(f"{prefix} {number}")
    return normalized


def _normalize_text_blob(*values: Optional[str]) -> str:
    parts = [value.strip() for value in values if isinstance(value, str) and value.strip()]
    if not parts:
        return ""
    return " ".join(parts).upper()


class DegreePlanService:
    @staticmethod
    def _normalize_program_code(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized.replace(" ", "-").upper()

    @staticmethod
    def _detect_requirement_category(course: Optional[dict], group_description: Optional[str]) -> Optional[str]:
        course = course or {}
        text = _normalize_text_blob(
            course.get("title"),
            course.get("code"),
            course.get("description"),
            group_description,
        )
        if not text:
            return None

        for category, rule in REQUIREMENT_CATEGORY_RULES.items():
            keywords = rule.get("requirement_keywords") or set()
            if any(keyword in text for keyword in keywords):
                return category
        return None

    @staticmethod
    def _completed_satisfies_category(category: str, completed_courses: List[dict]) -> bool:
        rule = REQUIREMENT_CATEGORY_RULES.get(category)
        if not rule:
            return False

        prefixes = rule.get("course_prefixes") or set()
        keywords = rule.get("course_keywords") or set()
        for completed in completed_courses or []:
            code = (completed.get("code") or "").upper().strip()
            title = (completed.get("title") or "").upper().strip()
            combined = _normalize_text_blob(code, title)

            if code and any(code.startswith(prefix) for prefix in prefixes):
                return True
            if combined and any(keyword in combined for keyword in keywords):
                return True
        return False

    @classmethod
    def _ensure_context_alignment(
        cls, db: Session, advisee_id: int
    ) -> Tuple[Optional[AdviseeProfile], Optional[AdviseeDegreeContext], Optional[DegreeRequirementSet]]:
        profile = (
            db.query(AdviseeProfile)
            .filter(AdviseeProfile.adviseeID == advisee_id)
            .first()
        )
        context = cls._load_context(db, advisee_id)
        requirement = None
        if context:
            requirement = (
                db.query(DegreeRequirementSet)
                .filter(DegreeRequirementSet.requirementSetID == context.requirementSetID)
                .first()
            )

        desired_code = cls._normalize_program_code(
            (profile.degree_plan or profile.major) if profile else None
        )
        requirement_code = cls._normalize_program_code(
            requirement.programCode if requirement else None
        )

        if not context or not requirement or (desired_code and requirement_code != desired_code):
            bootstrapped = cls._bootstrap_context_from_scraper(db, advisee_id)
            if bootstrapped:
                context = cls._load_context(db, advisee_id)
                if context:
                    requirement = (
                        db.query(DegreeRequirementSet)
                        .filter(DegreeRequirementSet.requirementSetID == context.requirementSetID)
                        .first()
                    )

        return profile, context, requirement

    @staticmethod
    def _load_context(db: Session, advisee_id: int) -> Optional[AdviseeDegreeContext]:
        return (
            db.query(AdviseeDegreeContext)
            .filter(AdviseeDegreeContext.adviseeID == advisee_id)
            .first()
        )

    @staticmethod
    def _infer_catalog_year(profile: AdviseeProfile) -> str:
        raw_value = (profile.degree_plan or "").strip()
        if not raw_value:
            return DEFAULT_CATALOG_YEAR

        match = CATALOG_YEAR_PATTERN.search(raw_value)
        if match:
            start_year = match.group(1)
            end_year = match.group(2)
            if end_year:
                return f"{start_year}-{end_year}"
            return start_year

        upper_value = raw_value.upper()
        if upper_value.startswith("CAT"):
            return upper_value

        return DEFAULT_CATALOG_YEAR

    @staticmethod
    def _build_keyword_list(*terms: Optional[str]) -> List[str]:
        keywords: List[str] = []
        for term in terms:
            if not term:
                continue
            tokens = re.split(r"[\s,/._-]+", term)
            keywords.extend(token for token in tokens if token)
        return keywords

    @staticmethod
    def _build_catalog_seed_url(program_code: Optional[str], catalog_year: Optional[str]) -> str:
        terms = [program_code or "", catalog_year or "", "degree plan pdf"]
        query = "+".join(
            quote_plus(term.strip())
            for term in terms
            if isinstance(term, str) and term.strip()
        )
        if not query:
            query = "degree+plan"

        if "{query}" in CATALOG_SEARCH_URL:
            return CATALOG_SEARCH_URL.format(query=query)

        suffix = ""
        if not CATALOG_SEARCH_URL.endswith(("?", "&")):
            suffix = "&" if "?" in CATALOG_SEARCH_URL else "?"

        return f"{CATALOG_SEARCH_URL}{suffix}{query}"

    @classmethod
    def _bootstrap_context_from_scraper(cls, db: Session, advisee_id: int) -> bool:
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
        keywords = cls._build_keyword_list(program_hint, major_code, catalog_year)
        seed_url = cls._build_catalog_seed_url(
            program_hint or major_code, catalog_year
        )

        try:
            import_degree_plan_from_pdf_url(
                db,
                advisee_id,
                pdf_url=seed_url,
                required_keywords=keywords,
                create_validation=False,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logging.warning(
                "Auto degree plan bootstrap failed for advisee %s (program=%s, catalog=%s): %s",
                advisee_id,
                program_hint or major_code,
                catalog_year,
                exc,
            )
            return False

    @staticmethod
    def _collect_courses_from_schedules(db: Session, advisee_id: int) -> List[dict]:
        """Build a de-duplicated list of courses pulled from the advisee's schedules."""
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
                case((Schedule.status == ScheduleStatusEnum.APPROVED, 0), else_=1),
                Schedule.createdWhen.desc(),
            )
            .all()
        )

        if not schedules:
            return []

        seen_sections: Set[int] = set()
        raw_courses: List[dict] = []
        for schedule in schedules:
            term_label = schedule.term.code if schedule.term else None
            schedule_status = (
                schedule.status.value
                if hasattr(schedule.status, "value")
                else str(schedule.status)
            )
            course_status = (
                "COMPLETED"
                if schedule_status == ScheduleStatusEnum.APPROVED.value
                else "PLANNED"
            )

            for cls in schedule.classes:
                if cls.sectionID in seen_sections:
                    continue
                seen_sections.add(cls.sectionID)

                section = cls.section
                course: Optional[Course] = section.course if section else None
                code = (course.courseName or "").strip() if course and course.courseName else ""
                if not code and section and section.crn:
                    code = section.crn

                title = course.courseName if course else None
                if course and course.description:
                    title = course.description
                elif not title and section and section.description:
                    title = section.description

                credits = 0.0
                if course and course.credits:
                    try:
                        credits = float(course.credits)
                    except (TypeError, ValueError):
                        credits = 0.0
                if credits <= 0:
                    credits = 3.0

                raw_courses.append(
                    {
                        "code": code or f"CLASS-{cls.classID}",
                        "title": title,
                        "credits": credits,
                        "term": term_label,
                        "status": course_status,
                    }
                )

        return _serialize_completed_courses(raw_courses)

    @staticmethod
    def _collect_courses_from_transcript(db: Session, advisee_id: int) -> List[dict]:
        enrollments = TranscriptService._load_enrollments(db, advisee_id)
        if not enrollments:
            return []

        terms = TranscriptService._build_terms(enrollments)
        completed: List[dict] = []
        for term in terms:
            for course in term.courses:
                status = (course.status or "").lower()
                if status != "completed":
                    continue
                completed.append(
                    {
                        "code": (course.courseCode or "").upper(),
                        "title": course.courseTitle,
                        "credits": float(course.credits or 0),
                        "term": term.term,
                        "status": "COMPLETED",
                    }
                )

        return completed

    @staticmethod
    def _expand_requirement_codes(course: dict, group_description: Optional[str]) -> Set[str]:
        codes = set()
        codes.update(_extract_codes_from_text(course.get("code")))
        codes.update(_extract_codes_from_text(course.get("title")))
        codes.update(_extract_codes_from_text(course.get("description")))
        if not codes and group_description:
            codes.update(_extract_codes_from_text(group_description))
        return codes

    @staticmethod
    def create_requirement_set(
        db: Session, payload: DegreeRequirementSetCreate
    ) -> DegreeRequirementSet:
        requirement_groups = [group.dict() for group in payload.requirementGroups]
        record = DegreeRequirementSet(
            programCode=payload.programCode,
            catalogYear=payload.catalogYear,
            programName=payload.programName,
            totalCredits=payload.totalCredits,
            requirementData=requirement_groups,
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
            query = query.filter(DegreeRequirementSet.programCode == program_code)
        return query.order_by(DegreeRequirementSet.updatedAt.desc()).all()

    @staticmethod
    def upsert_context(
        db: Session, advisee_id: int, payload: AdviseeContextUpsert
    ) -> AdviseeDegreeContext:
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
        if context is None:
            context = AdviseeDegreeContext(
                adviseeID=advisee_id, requirementSetID=requirement.requirementSetID
            )
            db.add(context)

        context.requirementSetID = requirement.requirementSetID
        context.completedCourses = _serialize_completed_courses(
            [course.dict() for course in payload.completedCourses]
        )
        context.overrides = payload.overrides
        context.notes = payload.notes

        db.commit()
        db.refresh(context)
        return context

    @staticmethod
    def get_advisee_summary(db: Session, advisee_id: int):
        profile, context, requirement = DegreePlanService._ensure_context_alignment(db, advisee_id)

        latest_validation = (
            db.query(DegreePlanValidation)
            .filter(DegreePlanValidation.adviseeID == advisee_id)
            .order_by(DegreePlanValidation.createdAt.desc())
            .first()
        )

        completed_courses = DegreePlanService._collect_courses_from_transcript(
            db, advisee_id
        )
        if not completed_courses:
            completed_courses = DegreePlanService._collect_courses_from_schedules(
                db, advisee_id
            )
        if context and completed_courses:
            # Surface live data in the summary without mutating the DB record permanently.
            context.completedCourses = completed_courses

        requirement_payload = None
        if requirement:
            requirement_payload = DegreeRequirementSetResponse(
                requirementSetID=requirement.requirementSetID,
                programCode=(profile.major if profile else None) or requirement.programCode,
                catalogYear=requirement.catalogYear,
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
        elif profile:
            requirement_payload = DegreeRequirementSetResponse(
                requirementSetID=0,
                programCode=profile.major or "",
                catalogYear=DEFAULT_CATALOG_YEAR,
                programName=profile.degree_plan or profile.major or "Program",
                totalCredits=float(profile.credits_completed or 0),
                requirementGroups=[],
                sourceDocument=None,
                createdAt=profile.dateCreated or datetime.utcnow(),
                updatedAt=profile.lastUpdated or datetime.utcnow(),
            )

        return {
            "context": context,
            "requirementSet": requirement_payload,
            "latestValidation": _normalize_validation(latest_validation),
        }

    @staticmethod
    def enqueue_validation(
        db: Session,
        advisee_id: int,
        run_type: ValidationRunType,
        background_tasks: BackgroundTasks,
        triggered_by: Optional[int] = None,
    ) -> DegreePlanValidation:
        _, context, _ = DegreePlanService._ensure_context_alignment(db, advisee_id)
        if not context:
            raise HTTPException(status_code=404, detail="Degree context not found")

        validation = DegreePlanValidation(
            adviseeID=advisee_id,
            contextID=context.contextID,
            requirementSetID=context.requirementSetID,
            status=ValidationStatus.PENDING,
            runType=run_type,
            triggeredBy=triggered_by,
        )
        db.add(validation)
        db.commit()
        db.refresh(validation)

        background_tasks.add_task(process_validation_job, validation.validationID)
        return _normalize_validation(validation)

    @staticmethod
    def list_validations(db: Session, advisee_id: int) -> List[DegreePlanValidation]:
        results = (
            db.query(DegreePlanValidation)
            .filter(DegreePlanValidation.adviseeID == advisee_id)
            .order_by(DegreePlanValidation.createdAt.desc())
            .all()
        )
        return [_normalize_validation(item) for item in results]

    @staticmethod
    def _process_validation(db: Session, validation_id: int):
        validation = (
            db.query(DegreePlanValidation)
            .filter(DegreePlanValidation.validationID == validation_id)
            .first()
        )
        if not validation:
            return

        # Mark running
        validation.status = ValidationStatus.RUNNING
        validation.startedAt = datetime.utcnow()
        db.commit()
        db.refresh(validation)

        context = validation.context
        requirement = validation.requirementSet

        if context is None or requirement is None:
            validation.status = ValidationStatus.ERROR
            validation.message = "Missing requirement data"
            validation.finishedAt = datetime.utcnow()
            validation.issues = []
            db.commit()
            return

        # === 1. Collect completed courses (schedule or transcript)
        completed_courses = DegreePlanService._collect_courses_from_transcript(
            db, validation.adviseeID
        )
        if not completed_courses:
            completed_courses = context.completedCourses or []
        else:
            context.completedCourses = completed_courses

        completed_codes = {
            (course.get("code") or "").upper().strip()
            for course in completed_courses
        }

        requirement_groups = requirement.requirementData or []
        issues = []
        total_required_credits = float(requirement.totalCredits or 0)
        completed_credits = sum(float(c.get("credits", 0)) for c in completed_courses)

        # ----------------------------------------
        # CATEGORY DETECTION HELPER (Local)
        # ----------------------------------------
        def detect_category_group(group, courses):
            description = group.get("description", "")
            for course in courses:
                category = DegreePlanService._detect_requirement_category(course, description)
                if category:
                    return category
            return None

        # === 3. Validate each requirement group
        for group in requirement_groups:
            group_id = group.get("id") or group.get("title")
            group_title = group.get("title", "Requirement Group")
            group_courses = group.get("courses", [])
            group_description = group.get("description", "")

            missing_list = []

            # ---------------------------------------------
            # NEW — CATEGORY GROUP HANDLING
            # ---------------------------------------------
            detected_category = detect_category_group(group, group_courses)

            if detected_category:
                # If student already satisfied category → OK
                if DegreePlanService._completed_satisfies_category(
                    detected_category, completed_courses
                ):
                    continue

                # Otherwise → ONE missing requirement entry
                issues.append(
                    {
                        "requirementId": group_id,
                        "message": f"Missing requirement: {REQUIREMENT_CATEGORY_RULES[detected_category]['label']}",
                        "missingCourses": [
                            REQUIREMENT_CATEGORY_RULES[detected_category]["label"]
                        ],
                    }
                )
                continue  # Skip standard course-by-course checking

            # ------------------------------------------------
            # NORMAL SPECIFIC COURSE VALIDATION
            # ------------------------------------------------
            for course in group_courses:
                course = course or {}
                expanded_codes = DegreePlanService._expand_requirement_codes(
                    course, group_description
                )

                # ------------------------------------------------
                # NEW LOGIC — If no specific course numbers found,
                # DO NOT treat optional choice items as required.
                # ------------------------------------------------
                if not expanded_codes:
                    continue  # skip optional “choose from these” items

                # If ANY acceptable code matches → satisfied
                if not any(code in completed_codes for code in expanded_codes):
                    missing_list.append("/".join(sorted(expanded_codes)))

            # Report missing items for this requirement group
            if missing_list:
                issues.append(
                    {
                        "requirementId": group_id,
                        "message": f"Missing {len(missing_list)} requirement(s) in {group_title}",
                        "missingCourses": missing_list,
                    }
                )

        # === 4. Compute completion percent
        if total_required_credits > 0:
            completion_percent = min(
                100.0,
                round((completed_credits / total_required_credits) * 100, 2)
            )
        else:
            completion_percent = 0.0

        # === 5. Save validation result
        validation.completionPercent = completion_percent
        validation.issues = issues
        validation.status = ValidationStatus.PASSED if not issues else ValidationStatus.FAILED
        validation.message = (
            "All requirements satisfied." if not issues else "Outstanding requirements."
        )
        validation.finishedAt = datetime.utcnow()

        db.commit()
        db.refresh(validation)




def process_validation_job(validation_id: int):
    db = SessionLocal()
    try:
        DegreePlanService._process_validation(db, validation_id)
    finally:
        db.close()
