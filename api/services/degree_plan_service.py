from datetime import datetime
from typing import List, Optional
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from db.database import SessionLocal
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


class DegreePlanService:
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
        db.commit()
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

        return {
            "context": context,
            "requirementSet": requirement,
            "latestValidation": latest_validation,
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
        return validation

    @staticmethod
    def list_validations(db: Session, advisee_id: int) -> List[DegreePlanValidation]:
        return (
            db.query(DegreePlanValidation)
            .filter(DegreePlanValidation.adviseeID == advisee_id)
            .order_by(DegreePlanValidation.createdAt.desc())
            .all()
        )

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
            db.commit()
            return

        completed_courses = context.completedCourses or []
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
