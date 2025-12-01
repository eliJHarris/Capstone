from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.advisee import AdviseeProfile
from models.user import User
from schemas.advisee import AdviseeListItem


class AdviseeService:
  """Service helpers for listing advisees and their metadata."""

  @staticmethod
  def list_advisees(
    db: Session,
    advisor_id: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
  ) -> List[AdviseeListItem]:
    query = db.query(AdviseeProfile, User).join(User, User.userID == AdviseeProfile.userID)

    if advisor_id is not None:
      query = query.filter(AdviseeProfile.advisorID == advisor_id)

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
    for profile, user in rows:
      advisees.append(
        AdviseeListItem(
          adviseeID=profile.adviseeID,
          userID=user.userID,
          name=user.username,
          email=user.email,
          major=profile.major,
          degreePlan=profile.degree_plan,
          classification=profile.classification,
          gpa=float(profile.gpa) if profile.gpa is not None else None,
          creditsCompleted=profile.credits_completed,
          status=profile.status,
          advisorID=profile.advisorID,
          updatedAt=profile.lastUpdated,
        )
      )

    return advisees
