from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.advisor import AdvisorProfile
from models.user import User
from models.advisee import AdviseeProfile
from schemas.advisee import (
    AdviseeCreate,
    AdviseeListItem,
    AdviseeResponse,
    AdviseeStatus,
    AdviseeUpdate,
    Classification,
)


class AdviseeService:
    """Service helpers for advisee CRUD and listing logic."""

    @staticmethod
    def list_advisees(
        db: Session,
        advisor_id: Optional[int] = None,
        search: Optional[str] = None,
        advisee_id: Optional[int] = None,
        user_id: Optional[int] = None,
        major: Optional[str] = None,
        degree_plan: Optional[str] = None,
        classification: Optional[Classification] = None,
        gpa: Optional[float] = None,
        credits_completed: Optional[int] = None,
        status: Optional[AdviseeStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[AdviseeListItem]:
        query = (
            db.query(AdviseeProfile, User, AdvisorProfile)
            .join(User, User.userID == AdviseeProfile.userID)
            .outerjoin(AdvisorProfile, AdvisorProfile.advisorID == AdviseeProfile.advisorID)
        )

        if advisee_id is not None:
            query = query.filter(AdviseeProfile.adviseeID == advisee_id)
        if user_id is not None:
            query = query.filter(AdviseeProfile.userID == user_id)
        if advisor_id is not None:
            query = query.filter(AdviseeProfile.advisorID == advisor_id)
        if major:
            query = query.filter(AdviseeProfile.major == major)
        if degree_plan:
            query = query.filter(AdviseeProfile.degree_plan == degree_plan)
        if classification:
            query = query.filter(AdviseeProfile.classification == classification)
        if gpa is not None:
            query = query.filter(AdviseeProfile.gpa == gpa)
        if credits_completed is not None:
            query = query.filter(AdviseeProfile.credits_completed == credits_completed)
        if status:
            query = query.filter(AdviseeProfile.status == status)

        if search:
            like = f"%{search}%"
            query = query.filter(
                or_(
                    User.username.ilike(like),
                    User.email.ilike(like),
                    AdviseeProfile.major.ilike(like),
                )
            )

        rows = query.order_by(User.username.asc()).offset(skip).limit(limit).all()

        advisees: List[AdviseeListItem] = []
        for profile, user, advisor in rows:
            advisees.append(
                AdviseeListItem(
                    adviseeID=profile.adviseeID,
                    userID=user.userID,
                    name=user.username,
                    email=user.email,
                    advisorName=advisor.name if advisor else None,
                    major=profile.major,
                    degreePlan=profile.degree_plan,
                    classification=profile.classification.value
                    if hasattr(profile.classification, "value")
                    else profile.classification,
                    gpa=float(profile.gpa) if profile.gpa is not None else None,
                    creditsCompleted=profile.credits_completed,
                    status=profile.status.value if hasattr(profile.status, "value") else profile.status,
                    advisorID=profile.advisorID,
                    updatedAt=profile.lastUpdated,
                )
            )

        return advisees

    @staticmethod
    def get_advisee_by_id(db: Session, advisee_id: int) -> AdviseeResponse:
        advisee = db.query(AdviseeProfile).filter(AdviseeProfile.adviseeID == advisee_id).first()

        if not advisee:
            raise HTTPException(status_code=404, detail="Advisee profile not found")

        return advisee

    @staticmethod
    def create_advisee(db: Session, advisee_data: AdviseeCreate) -> AdviseeResponse:
        user = db.query(User).filter(User.userID == advisee_data.userID).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {advisee_data.userID} not found",
            )

        advisor_id = advisee_data.advisorID
        if advisor_id:
            if advisor_id == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="advisorID cannot be 0; use null for no advisor",
                )

            advisor = db.query(AdvisorProfile).filter(AdvisorProfile.advisorID == advisor_id).first()
            if not advisor:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Advisor with ID {advisor_id} not found",
                )

        existing = db.query(AdviseeProfile).filter(AdviseeProfile.userID == advisee_data.userID).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Advisee profile already exists for user {advisee_data.userID}",
            )

        new_advisee = AdviseeProfile(
            **advisee_data.dict(exclude={"advisorID"}),
            advisorID=advisor_id if advisor_id else None,
            dateCreated=datetime.now(),
            lastUpdated=datetime.now(),
        )

        db.add(new_advisee)
        db.commit()
        db.refresh(new_advisee)

        return new_advisee

    @staticmethod
    def update_advisee(db: Session, advisee_id: int, advisee_data: AdviseeUpdate) -> AdviseeResponse:
        advisee = db.query(AdviseeProfile).filter(AdviseeProfile.adviseeID == advisee_id).first()

        if not advisee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Advisee profile with ID {advisee_id} not found",
            )

        update_fields = advisee_data.dict(exclude_unset=True)

        if "advisorID" in update_fields:
            advisor_id = update_fields["advisorID"]
            if advisor_id is not None:
                advisor = db.query(AdvisorProfile).filter(AdvisorProfile.advisorID == advisor_id).first()
                if not advisor:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Advisor with ID {advisor_id} not found",
                    )

        for field, value in update_fields.items():
            setattr(advisee, field, value)

        advisee.lastUpdated = datetime.now()

        db.commit()
        db.refresh(advisee)

        return advisee

    @staticmethod
    def delete_advisee(db: Session, advisee_id: int):
        advisee = db.query(AdviseeProfile).filter(AdviseeProfile.adviseeID == advisee_id).first()

        if not advisee:
            raise HTTPException(status_code=404, detail="Advisee profile not found")

        db.delete(advisee)
        db.commit()
        return {"message": "Advisee profile deleted successfully"}
