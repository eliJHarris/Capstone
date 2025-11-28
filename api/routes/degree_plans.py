from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
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
from services.degree_plan_service import DegreePlanService
from models.degree_plan import ValidationRunType

router = APIRouter(prefix="/degree-plans", tags=["degree plans"])


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


@router.post(
    "/advisees/{advisee_id}/context",
    response_model=AdviseeContextResponse,
)
def upsert_advisee_context(
    advisee_id: int,
    payload: AdviseeContextUpsert,
    background_tasks: BackgroundTasks,
    auto_validate: bool = Query(
        True,
        description="Trigger an automatic validation after updating context",
    ),
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
            # ignore missing context errors since we just created it
            pass
    return context


@router.get(
    "/advisees/{advisee_id}/summary",
    response_model=AdviseePlanSummary,
)
def get_advisee_summary(
    advisee_id: int,
    db: Session = Depends(get_db),
):
    return DegreePlanService.get_advisee_summary(db, advisee_id)


@router.post(
    "/advisees/{advisee_id}/validate",
    response_model=DegreePlanValidationResponse,
)
def request_validation(
    advisee_id: int,
    payload: ValidationRequest = ValidationRequest(),
    background_tasks: BackgroundTasks,
    run_type: ValidationRunTypeEnum = ValidationRunTypeEnum.MANUAL,
    db: Session = Depends(get_db),
):
    validation = DegreePlanService.enqueue_validation(
        db=db,
        advisee_id=advisee_id,
        run_type=ValidationRunType(run_type.value),
        triggered_by=payload.triggeredBy,
        background_tasks=background_tasks,
    )
    return validation


@router.get(
    "/advisees/{advisee_id}/validations",
    response_model=List[DegreePlanValidationResponse],
)
def list_validations(
    advisee_id: int,
    db: Session = Depends(get_db),
):
    return DegreePlanService.list_validations(db, advisee_id)
