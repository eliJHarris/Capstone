from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db

from schemas.advisor import AdvisorProfileCreate, AdvisorProfileResponse, AdvisorProfileUpdate

from services.advisor_service import AdvisorProfileService


router = APIRouter(prefix="/advisors", tags=["advisors"])


def _get_advisor_profiles(
    advisorID: Optional[int] = Query(None, description="Filter by advisor ID(matches user id)"),
    name: Optional[str] = Query(None, description="Filter by advisor name"),
    office: Optional[str] = Query(None, description="Filter by advisor office"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    return AdvisorProfileService.get_all_advisors(
        db=db,
        advisorID=advisorID,
        name=name,
        office=office,
        skip=skip,
        limit=limit
    )


@router.get("/", response_model=List[AdvisorProfileResponse])
def get_advisor_profiles(
    advisorID: Optional[int] = Query(None, description="Filter by advisor ID(matches user id)"),
    name: Optional[str] = Query(None, description="Filter by advisor name"),
    office: Optional[str] = Query(None, description="Filter by advisor office"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    return _get_advisor_profiles(advisorID, name, office, skip, limit, db)


def _get_advisor_profile(advisor_id: int, db: Session):
    return AdvisorProfileService.get_by_id(db=db, advisor_id=advisor_id)


@router.get("/{advisor_id}", response_model=AdvisorProfileResponse)
def get_advisor_profile(
    advisor_id: int,
    db: Session = Depends(get_db)
):
    return _get_advisor_profile(advisor_id, db)


def _create_advisor_profile(profile: AdvisorProfileCreate, db: Session):
    return AdvisorProfileService.create(db=db, profile_data=profile)


@router.post("/", response_model=AdvisorProfileResponse, status_code=201)
def create_advisor_profile(
    profile: AdvisorProfileCreate,
    db: Session = Depends(get_db)
):
    return _create_advisor_profile(profile, db)


def _update_advisor_profile(advisor_id: int, profile: AdvisorProfileUpdate, db: Session):
    return AdvisorProfileService.update(db=db, advisor_id=advisor_id, profile_data=profile)


@router.put("/{advisor_id}", response_model=AdvisorProfileResponse)
def update_advisor_profile(
    advisor_id: int,
    profile: AdvisorProfileUpdate,
    db: Session = Depends(get_db)
):
    return _update_advisor_profile(advisor_id, profile, db)


def _delete_advisor_profile(advisor_id: int, db: Session):
    return AdvisorProfileService.delete(db=db, advisor_id=advisor_id)


@router.delete("/{advisor_id}")
def delete_advisor_profile(
    advisor_id: int,
    db: Session = Depends(get_db)
):
    return _delete_advisor_profile(advisor_id, db)
