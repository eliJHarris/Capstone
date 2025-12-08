from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from models.degree_plan import DegreePlanValidation, ValidationRunType
from models.user import User
from schemas.degree_plan import (
    AdviseeContextResponse,
    AdviseeContextUpsert,
    AdviseePlanSummary,
    DegreePlanValidationResponse,
    DegreeRequirementSetCreate,
    DegreeRequirementSetResponse,
    ValidationRequest,
    ValidationRunTypeEnum,
)
from services.degree_plan_service import DegreePlanService, normalize_catalog_display

router = APIRouter(prefix="/degree-plans", tags=["degree plans"])


# ------------------------------
# REQUIREMENT SET MANAGEMENT
# ------------------------------
@router.post(
    "/requirements",
    response_model=DegreeRequirementSetResponse,
    status_code=201,
)
def create_requirement_set(
    payload: DegreeRequirementSetCreate,
    db: Session = Depends(get_db),
):
    return DegreePlanService.create_requirement_set(db, payload)


@router.get("/requirements", response_model=List[DegreeRequirementSetResponse])
def list_requirement_sets(
    program_code: Optional[str] = Query(None, description="Filter by program code"),
    db: Session = Depends(get_db),
):
    return DegreePlanService.list_requirement_sets(db, program_code)


# ------------------------------
# CONTEXT UPSERT
# ------------------------------
@router.post(
    "/advisees/{advisee_id}/context",
    response_model=AdviseeContextResponse,
)
def upsert_advisee_context(
    advisee_id: int,
    payload: AdviseeContextUpsert,
    background_tasks: BackgroundTasks,
    auto_validate: bool = Query(True),
    db: Session = Depends(get_db),
):
    context = DegreePlanService.upsert_context(db, advisee_id, payload)

    if auto_validate:
        try:
            DegreePlanService.enqueue_validation(
                db=db,
                advisee_id=advisee_id,
                run_type=ValidationRunType.AUTOMATIC,
                background_tasks=background_tasks,
            )
        except HTTPException:
            pass

    return context


# ------------------------------
# SUMMARY ENDPOINT
# ------------------------------
@router.get("/advisees/{advisee_id}/summary")
def get_advisee_summary(
    advisee_id: int,
    allow_bootstrap: bool = Query(True),
    db: Session = Depends(get_db),
):
    return DegreePlanService.get_advisee_summary(db, advisee_id, allow_bootstrap=allow_bootstrap)


# ------------------------------
# VALIDATION TRIGGER
# ------------------------------
@router.post(
    "/advisees/{advisee_id}/validate",
    response_model=DegreePlanValidationResponse,
)
def request_validation(
    advisee_id: int,
    background_tasks: BackgroundTasks,
    payload: ValidationRequest = ValidationRequest(),
    run_type: ValidationRunTypeEnum = ValidationRunTypeEnum.MANUAL,
    db: Session = Depends(get_db),
):
    return DegreePlanService.enqueue_validation(
        db=db,
        advisee_id=advisee_id,
        run_type=ValidationRunType(run_type.value),
        triggered_by=payload.triggeredBy,
        background_tasks=background_tasks,
    )


@router.get(
    "/advisees/{advisee_id}/validations",
    response_model=List[DegreePlanValidationResponse],
)
def list_validations(
    advisee_id: int,
    db: Session = Depends(get_db),
):
    return DegreePlanService.list_validations(db, advisee_id)


# ------------------------------
# NEW CONTEXT SNAPSHOT ENDPOINT
# MATCHES DEGREE PLAN UI NEEDS
# ------------------------------
@router.get("/advisees/{advisee_id}/context")
def get_degree_plan_context(
    advisee_id: int,
    allow_bootstrap: bool = Query(True),
    db: Session = Depends(get_db),
):
    profile, context, requirement = DegreePlanService._ensure_context(
        db,
        advisee_id,
        allow_bootstrap=allow_bootstrap,
    )

    if not profile:
        raise HTTPException(status_code=404, detail="Advisee profile not found")

    # Student name
    user = db.query(User).filter(User.userID == profile.userID).first()
    profile_name = (user.username if user else None) or f"Advisee {advisee_id}"

    # Requirement Set (raw dict, NOT Pydantic — avoids validation errors)
    requirement_payload = None
    catalog_year = None

    if requirement:
        requirement_payload = {
            "requirementSetID": requirement.requirementSetID,
            "programCode": profile.major or requirement.programCode,
            "catalogYear": normalize_catalog_display(requirement.catalogYear),
            "programName": profile.degree_plan or requirement.programName,
            "totalCredits": requirement.totalCredits,
            "requirementGroups": requirement.requirementData or [],
            "sourceDocument": requirement.sourceDocument,
            "createdAt": requirement.createdAt,
            "updatedAt": requirement.updatedAt,
        }
        catalog_year = requirement_payload["catalogYear"]

    # Latest validation
    latest_validation = (
        db.query(DegreePlanValidation)
        .filter(DegreePlanValidation.adviseeID == advisee_id)
        .order_by(DegreePlanValidation.createdAt.desc())
        .first()
    )

    validation_payload = None
    if latest_validation:
        computed = None
        try:
            computed = DegreePlanService.validate_degree_plan(db, advisee_id)
        except HTTPException:
            computed = None
        normalized = DegreePlanService._normalize_validation_record(
            latest_validation,
            extras=computed,
        )
        validation_payload = DegreePlanValidationResponse.from_orm(normalized)

    return {
        "adviseeID": advisee_id,
        "name": profile_name,
        "major": profile.major,
        "classification": getattr(profile.classification, "value", profile.classification),
        "catalogYear": catalog_year,
        "completedCourses": context.completedCourses if context else [],
        "requirementSet": requirement_payload,
        "validation": validation_payload,
    }
