from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from schemas.advisee import (
    AdviseeCreate,
    AdviseeListItem,
    AdviseeResponse,
    AdviseeStatus,
    AdviseeUpdate,
    Classification,
)
from services.advisee_service import AdviseeService

router = APIRouter(prefix="/advisees", tags=["advisees"])


def _list_advisees(
    advisor_id: Optional[int],
    advisor_id_legacy: Optional[int],
    advisee_id: Optional[int],
    advisee_id_legacy: Optional[int],
    user_id: Optional[int],
    user_id_legacy: Optional[int],
    major: Optional[str],
    degree_plan: Optional[str],
    classification: Optional[Classification],
    gpa: Optional[float],
    credits_completed: Optional[int],
    status: Optional[AdviseeStatus],
    search: Optional[str],
    skip: int,
    limit: int,
    db: Session,
):
    return AdviseeService.list_advisees(
        db=db,
        advisor_id=advisor_id if advisor_id is not None else advisor_id_legacy,
        advisee_id=advisee_id if advisee_id is not None else advisee_id_legacy,
        user_id=user_id if user_id is not None else user_id_legacy,
        major=major,
        degree_plan=degree_plan,
        classification=classification,
        gpa=gpa,
        credits_completed=credits_completed,
        status=status,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/", response_model=List[AdviseeListItem])
def list_advisees_with_slash(
    advisor_id: Optional[int] = Query(None, description="Filter by advisor ID"),
    advisor_id_legacy: Optional[int] = Query(
        None, alias="advisorID", include_in_schema=False
    ),
    advisee_id: Optional[int] = Query(None, description="Filter by advisee ID"),
    advisee_id_legacy: Optional[int] = Query(
        None, alias="adviseeID", include_in_schema=False
    ),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    user_id_legacy: Optional[int] = Query(None, alias="userID", include_in_schema=False),
    major: Optional[str] = Query(None, description="Filter by major"),
    degree_plan: Optional[str] = Query(None, description="Filter by degree plan"),
    classification: Optional[Classification] = Query(None, description="Filter by classification"),
    gpa: Optional[float] = Query(None, description="Filter by GPA"),
    credits_completed: Optional[int] = Query(None, description="Filter by credits completed"),
    status: Optional[AdviseeStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name, email, or major"),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Maximum records to return"),
    db: Session = Depends(get_db),
):
    return _list_advisees(
        advisor_id,
        advisor_id_legacy,
        advisee_id,
        advisee_id_legacy,
        user_id,
        user_id_legacy,
        major,
        degree_plan,
        classification,
        gpa,
        credits_completed,
        status,
        search,
        skip,
        limit,
        db,
    )


@router.get("", response_model=List[AdviseeListItem], include_in_schema=False)
def list_advisees_no_slash(
    advisor_id: Optional[int] = Query(None, description="Filter by advisor ID"),
    advisor_id_legacy: Optional[int] = Query(
        None, alias="advisorID", include_in_schema=False
    ),
    advisee_id: Optional[int] = Query(None, description="Filter by advisee ID"),
    advisee_id_legacy: Optional[int] = Query(
        None, alias="adviseeID", include_in_schema=False
    ),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    user_id_legacy: Optional[int] = Query(None, alias="userID", include_in_schema=False),
    major: Optional[str] = Query(None, description="Filter by major"),
    degree_plan: Optional[str] = Query(None, description="Filter by degree plan"),
    classification: Optional[Classification] = Query(None, description="Filter by classification"),
    gpa: Optional[float] = Query(None, description="Filter by GPA"),
    credits_completed: Optional[int] = Query(None, description="Filter by credits completed"),
    status: Optional[AdviseeStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name, email, or major"),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Maximum records to return"),
    db: Session = Depends(get_db),
):
    return _list_advisees(
        advisor_id,
        advisor_id_legacy,
        advisee_id,
        advisee_id_legacy,
        user_id,
        user_id_legacy,
        major,
        degree_plan,
        classification,
        gpa,
        credits_completed,
        status,
        search,
        skip,
        limit,
        db,
    )


@router.get("/{advisee_id}", response_model=AdviseeResponse)
def get_advisee(advisee_id: int, db: Session = Depends(get_db)):
    return AdviseeService.get_advisee_by_id(db=db, advisee_id=advisee_id)


@router.post("/", response_model=AdviseeResponse, status_code=201)
def create_advisee(advisee: AdviseeCreate, db: Session = Depends(get_db)):
    return AdviseeService.create_advisee(db=db, advisee_data=advisee)


@router.put("/{advisee_id}", response_model=AdviseeResponse)
def update_advisee(
    advisee_id: int,
    advisee: AdviseeUpdate,
    db: Session = Depends(get_db),
):
    return AdviseeService.update_advisee(
        db=db,
        advisee_id=advisee_id,
        advisee_data=advisee,
    )


@router.delete("/{advisee_id}")
def delete_advisee(advisee_id: int, db: Session = Depends(get_db)):
    return AdviseeService.delete_advisee(db=db, advisee_id=advisee_id)
