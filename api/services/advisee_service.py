from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from fastapi import HTTPException, status

from models.advisor import AdvisorProfile
from models.user import User
from models.advisee import AdviseeProfile
from schemas.advisee import (
    AdviseeCreate,
    AdviseeUpdate,
    AdviseeResponse,
    AdviseeStatus,
    Classification
)

class AdviseeProfileService:

    @staticmethod
    def get_all_advisees(
    db: Session,
    adviseeID: Optional[int] = None,
    userID: Optional[int] = None,
    advisorID: Optional[int] = None,
    major: Optional[str] = None,
    degree_plan: Optional[str] = None,
    classification: Optional[Classification] = None,
    gpa: Optional[float] = None,
    credits_completed: Optional[int] = None,
    status: Optional[AdviseeStatus] = None,
    skip: int = 0,
    limit: int = 100
    ) -> List[AdviseeResponse]:
        query = db.query(AdviseeProfile)

        # Apply filters
        if adviseeID:
            query = query.filter(AdviseeProfile.adviseeID == adviseeID)
        if userID:
            query = query.filter(AdviseeProfile.userID == userID)
        if advisorID:
            query = query.filter(AdviseeProfile.advisorID == advisorID)
        if major:
            query = query.filter(AdviseeProfile.major == major)
        if degree_plan:
            query = query.filter(AdviseeProfile.degree_plan == degree_plan)
        if classification:
            query = query.filter(AdviseeProfile.classification == classification)
        if gpa:
            query = query.filter(AdviseeProfile.gpa == gpa)
        if credits_completed:
            query = query.filter(AdviseeProfile.credits_completed == credits_completed)
        if status:
            query = query.filter(AdviseeProfile.status == status)

        advisees = query.offset(skip).limit(limit).all()

        # Build response with class count
        result = []
        for advisee in advisees:
            result.append(AdviseeResponse(
                adviseeID = advisee.adviseeID,
                userID = advisee.userID,
                advisorID = advisee.advisorID,
                major = advisee.major,
                degree_plan = advisee.degree_plan,
                classification = advisee.classification,
                gpa = advisee.gpa,
                credits_completed = advisee.credits_completed,
                status = advisee.status,
                dateCreated = advisee.dateCreated,
                lastUpdated = advisee.lastUpdated
            ))

        return result

    @staticmethod
    def get_advisee_by_id(db: Session, advisee_id: int):
        advisee = db.query(AdviseeProfile).filter(
            AdviseeProfile.adviseeID == advisee_id
        ).first()

        if not advisee:
            raise HTTPException(status_code=404, detail="Advisee profile not found")

        return advisee

    def create_advisee(db: Session, advisee_data: AdviseeCreate) -> AdviseeResponse:
        """
        Create a new advisee profile
        """
        # Verify user exists
        user = db.query(User).filter(User.userID == advisee_data.userID).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {advisee_data.userID} not found"
            )

        # Verify advisor exists if provided and not 0
        advisor_id = advisee_data.advisorID
        if advisor_id:
            if advisor_id == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="advisorID cannot be 0; use null for no advisor"
                )

            advisor = db.query(AdvisorProfile).filter(
                AdvisorProfile.advisorID == advisor_id
            ).first()
            if not advisor:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Advisor with ID {advisor_id} not found"
                )

        # Ensure user doesn't already have an advisee profile
        existing = db.query(AdviseeProfile).filter(
            AdviseeProfile.userID == advisee_data.userID
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Advisee profile already exists for user {advisee_data.userID}"
            )

        # Create new advisee, explicitly handle None for advisorID
        new_advisee = AdviseeProfile(
            **advisee_data.dict(exclude={"advisorID"}),
            advisorID=advisor_id if advisor_id else None,
            dateCreated=datetime.now(),
            lastUpdated=datetime.now()
        )

        db.add(new_advisee)
        db.commit()
        db.refresh(new_advisee)

        return new_advisee

    @staticmethod
    def update_advisee(db: Session, advisee_id: int, advisee_data: AdviseeUpdate) -> AdviseeResponse:
        """
        Update an existing advisee profile
        """
        advisee = db.query(AdviseeProfile).filter(
            AdviseeProfile.adviseeID == advisee_id
        ).first()

        if not advisee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Advisee profile with ID {advisee_id} not found"
            )

        update_fields = advisee_data.dict(exclude_unset=True)

        # Validate advisorID if provided
        if "advisorID" in update_fields:
            advisor_id = update_fields["advisorID"]
            if advisor_id is not None:
                advisor = db.query(AdvisorProfile).filter(
                    AdvisorProfile.advisorID == advisor_id
                ).first()
                if not advisor:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Advisor with ID {advisor_id} not found"
                    )

        # Update fields safely
        for field, value in update_fields.items():
            setattr(advisee, field, value)

        advisee.lastUpdated = datetime.now()

        db.commit()
        db.refresh(advisee)

        return advisee

    @staticmethod
    def delete_advisee(db: Session, advisee_id: int):
        advisee = db.query(AdviseeProfile).filter(
            AdviseeProfile.adviseeID == advisee_id
        ).first()

        if not advisee:
            raise HTTPException(status_code=404, detail="Advisee profile not found")

        db.delete(advisee)
        db.commit()
        return {"message": "Advisee profile deleted successfully"}
