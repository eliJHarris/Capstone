from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from fastapi import HTTPException, status

from models.advisor import AdvisorProfile
from models.user import User  # ensure this is correct path

from schemas.advisor import (
    AdvisorProfileCreate,
    AdvisorProfileUpdate,
    AdvisorProfileResponse
)


class AdvisorProfileService:

    @staticmethod
    def get_all_advisors(
        db: Session,
        advisorID: Optional[int] = None,
        name: Optional[str] = None,
        office: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AdvisorProfileResponse]:
        query = db.query(AdvisorProfile)

        # Apply filters
        if advisorID:
            query = query.filter(AdvisorProfile.advisorID == advisorID)
        if name:
            query = query.filter(AdvisorProfile.name == name)
        if office:
            query = query.filter(AdvisorProfile.office == office)

        advisors = query.offset(skip).limit(limit).all()

        # Build response with class count
        result = []
        for advisor in advisors:
            result.append(AdvisorProfileResponse(
                advisorID=advisor.advisorID,
                name=advisor.name,
                office=advisor.office,
                createdWhen=advisor.createdWhen
            ))

        return result

    @staticmethod
    def get_by_id(db: Session, advisor_id: int) -> AdvisorProfileResponse:
        profile = db.query(AdvisorProfile).filter(
            AdvisorProfile.advisorID == advisor_id
        ).first()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Advisor profile with ID {advisor_id} not found"
            )

        return profile

    @staticmethod
    def create(db: Session, profile_data: AdvisorProfileCreate) -> AdvisorProfileResponse:
        # Confirm advisorID is a real user
        user = db.query(User).filter(User.userID == profile_data.advisorID).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {profile_data.advisorID} not found"
            )

        # Enforce single profile per advisor
        existing = db.query(AdvisorProfile).filter(
            AdvisorProfile.advisorID == profile_data.advisorID
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Advisor profile already exists for user {profile_data.advisorID}"
            )

        new_profile = AdvisorProfile(
            advisorID=profile_data.advisorID,
            name=profile_data.name,
            office=profile_data.office,
            createdWhen=datetime.now()
        )

        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)

        return new_profile

    @staticmethod
    def update(db: Session, advisor_id: int, profile_data: AdvisorProfileUpdate) -> AdvisorProfileResponse:
        profile = db.query(AdvisorProfile).filter(
            AdvisorProfile.advisorID == advisor_id
        ).first()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Advisor profile with ID {advisor_id} not found"
            )

        # Only update provided fields
        if profile_data.name is not None:
            profile.name = profile_data.name

        if profile_data.office is not None:
            profile.office = profile_data.office

        db.commit()
        db.refresh(profile)

        return profile

    @staticmethod
    def delete(db: Session, advisor_id: int):
        profile = db.query(AdvisorProfile).filter(
            AdvisorProfile.advisorID == advisor_id
        ).first()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Advisor profile with ID {advisor_id} not found"
            )

        db.delete(profile)
        db.commit()

        return {"message": f"Advisor profile {advisor_id} deleted successfully"}
