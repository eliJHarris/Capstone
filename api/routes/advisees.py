from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from db.database import get_db
from schemas.advisee import (
    AdviseeCreate,
    AdviseeUpdate,
    AdviseeResponse,
    AdviseeStatus,
    Classification
)
from services.advisee_service import AdviseeProfileService

router = APIRouter(
    prefix="/advisees",
    tags=["advisees"]
)


@router.get("/", response_model=List[AdviseeResponse])
def get_advisee_profiles(
    adviseeID: Optional[int] = Query(None, description="Filter by advisee ID"),
    userID: Optional[int] = Query(None, description="Filter by user ID"),
    advisorID: Optional[int] = Query(None, description="Filter by advisor id"),
    major: Optional[str] = Query(None, description="Filter by major"),
    degree_plan: Optional[str] = Query(None, description="Filter by degree plan"),
    classification: Optional[Classification] = Query(None, description="Filter by classification"),
    gpa: Optional[float] = Query(None, description="Filter by gpa"),
    credits_completed: Optional[int] = Query(None, description="Filter by credits completed"),
    status: Optional[AdviseeStatus] = Query(None, description="Filter by styatus"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    return AdviseeProfileService.get_all_advisees(
        db=db,
        adviseeID=adviseeID,
        userID=userID,
        advisorID=advisorID,
        major=major,
        degree_plan=degree_plan,
        classification=classification,
        gpa=gpa,
        credits_completed=credits_completed,
        status=status,
        skip=skip,
        limit=limit
    )


@router.get("/{advisee_id}", response_model=AdviseeResponse)
def get_advisee(advisee_id: int, db: Session = Depends(get_db)):
    return AdviseeProfileService.get_advisee_by_id(db=db, advisee_id=advisee_id)


@router.post("/", response_model=AdviseeResponse, status_code=201)
def create_advisee(advisee: AdviseeCreate, db: Session = Depends(get_db)):
    return AdviseeProfileService.create_advisee(db=db, advisee_data=advisee)


@router.put("/{advisee_id}", response_model=AdviseeResponse)
def update_advisee(
    advisee_id: int,
    advisee: AdviseeUpdate,
    db: Session = Depends(get_db)
):
    return AdviseeProfileService.update_advisee(
        db=db,
        advisee_id=advisee_id,
        advisee_data=advisee
    )


@router.delete("/{advisee_id}")
def delete_advisee(advisee_id: int, db: Session = Depends(get_db)):
    return AdviseeProfileService.delete_advisee(db=db, advisee_id=advisee_id)
