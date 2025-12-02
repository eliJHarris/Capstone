from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from db.database import get_db

from schemas.advisor import (
    AdvisorProfileCreate,
    AdvisorProfileUpdate,
    AdvisorProfileResponse
)

from services.advisor_service import AdvisorProfileService


router = APIRouter(
    prefix="/advisor",
    tags=["advisors"]
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
    """
    Get all advisor profiles.
    """
    return AdvisorProfileService.get_all_advisors(
        db=db,
        advisorID=advisorID,
        name=name,
        office=office,
        skip=skip,
        limit=limit
    )


@router.get("/{advisor_id}", response_model=AdvisorProfileResponse)
def get_advisor_profile(
    advisor_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific advisor profile by ID.
    """
    return AdvisorProfileService.get_by_id(db=db, advisor_id=advisor_id)


@router.post("/", response_model=AdvisorProfileResponse, status_code=201)
def create_advisor_profile(
    profile: AdvisorProfileCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new advisor profile.
    """
    return AdvisorProfileService.create(db=db, profile_data=profile)


@router.put("/{advisor_id}", response_model=AdvisorProfileResponse)
def update_advisor_profile(
    advisor_id: int,
    profile: AdvisorProfileUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing advisor profile.
    """
    return AdvisorProfileService.update(db=db, advisor_id=advisor_id, profile_data=profile)


@router.delete("/{advisor_id}")
def delete_advisor_profile(
    advisor_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete an advisor profile.
    """
    return AdvisorProfileService.delete(db=db, advisor_id=advisor_id)
