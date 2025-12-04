import enum

from sqlalchemy import Column, DateTime, DECIMAL, Enum, ForeignKey, Integer, String
from sqlalchemy.sql import func

from .base import Base


class Classification(str, enum.Enum):
    Freshman = "Freshman"
    Sophomore = "Sophomore"
    Junior = "Junior"
    Senior = "Senior"


class AdviseeStatus(str, enum.Enum):
    Active = "Active"
    Inactive = "Inactive"
    Graduated = "Graduated"
    Suspended = "Suspended"


class AdviseeProfile(Base):
    __tablename__ = "adviseeProfile"

    adviseeID = Column(Integer, primary_key=True, autoincrement=True, index=True)
    userID = Column(Integer, ForeignKey("users.userID", ondelete="CASCADE"), nullable=False, unique=True)
    advisorID = Column(Integer, ForeignKey("advisorProfile.advisorID", ondelete="SET NULL"), nullable=True)
    # Stored as program code; column name in DB is majorCode
    major = Column("majorCode", String(64), ForeignKey("majors.programCode", ondelete="RESTRICT"), nullable=False)
    degree_plan = Column(String(100))
    classification = Column(Enum(Classification), nullable=False)
    gpa = Column(DECIMAL(3, 2))
    credits_completed = Column(Integer, nullable=False, default=0)
    status = Column(Enum(AdviseeStatus), nullable=False, default=AdviseeStatus.Active)
    dateCreated = Column(DateTime, nullable=False, server_default=func.now())
    lastUpdated = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
