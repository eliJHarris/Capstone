from datetime import datetime
from typing import List, Optional, Set
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import case
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from db.database import SessionLocal
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
    ValidationIssue,
)


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


class DegreePlanService:
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
        context = (
            db.query(AdviseeDegreeContext)
            .filter(AdviseeDegreeContext.adviseeID == advisee_id)
            .first()
        )
        requirement = None
        if context:
            requirement = (
                db.query(DegreeRequirementSet)
                .filter(DegreeRequirementSet.requirementSetID == context.requirementSetID)
                .first()
            )

        latest_validation = (
            db.query(DegreePlanValidation)
            .filter(DegreePlanValidation.adviseeID == advisee_id)
            .order_by(DegreePlanValidation.createdAt.desc())
            .first()
        )

        schedule_courses = DegreePlanService._collect_courses_from_schedules(
            db, advisee_id
        )
        if context and schedule_courses:
            # Surface live schedule-backed courses in the summary without mutating the DB record.
            context.completedCourses = schedule_courses

        return {
            "context": context,
            "requirementSet": requirement,
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
        context = (
            db.query(AdviseeDegreeContext)
            .filter(AdviseeDegreeContext.adviseeID == advisee_id)
            .first()
        )
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
            if validation.issues is None:
                validation.issues = []
            db.commit()
            return

        completed_courses = context.completedCourses or []
        schedule_courses = DegreePlanService._collect_courses_from_schedules(
            db, validation.adviseeID
        )
        if schedule_courses:
            completed_courses = schedule_courses
        requirement_groups = requirement.requirementData or []

        completed_by_code = {
            (course.get("code") or "").upper(): course for course in completed_courses
        }
        completed_credits = sum(
            float(course.get("credits", 0)) for course in completed_courses
        )
        total_required = float(requirement.totalCredits or 0)
        issues: List[ValidationIssue] = []

        for group in requirement_groups:
            missing_courses: List[str] = []
            group_courses = group.get("courses", [])
            for course in group_courses:
                code = (course.get("code") or "").upper()
                if not code:
                    continue
                if code not in completed_by_code:
                    missing_courses.append(code)

            if missing_courses:
                issues.append(
                    ValidationIssue(
                        requirementId=group.get("id") or group.get("title"),
                        message=f"Missing {len(missing_courses)} course(s) in {group.get('title')}",
                        missingCourses=missing_courses,
                    )
                )

        completion_percent = 0.0
        if total_required > 0:
            completion_percent = min(
                100.0,
                round((completed_credits / total_required) * 100, 2),
            )

        validation.completionPercent = completion_percent
        validation.issues = [issue.dict() for issue in issues]
        validation.status = (
            ValidationStatus.PASSED if not issues else ValidationStatus.FAILED
        )
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
