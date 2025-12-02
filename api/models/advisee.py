from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, ForeignKey, Text, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

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


class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    ADVISOR = "ADVISOR"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = "users"

    userID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    isActive = Column(Boolean, nullable=False, default=True)
    createdDate = Column(DateTime, nullable=False, default=func.now())

class AdvisorProfile(Base):
    __tablename__ = "advisorProfile"

    advisorID = Column(Integer, ForeignKey("users.userID"), primary_key=True, index=True)
    name = Column(String(160), nullable=False)
    office = Column(String(160), nullable=True)
    createdWhen = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships

class AdviseeProfile(Base):
    __tablename__ = "adviseeProfile"

    adviseeID = Column(Integer, primary_key=True, autoincrement=True)
    userID = Column(Integer, ForeignKey("users.userID", ondelete="CASCADE"), unique=True, nullable=False)
    advisorID = Column(Integer, ForeignKey("advisorProfile.advisorID", ondelete="SET NULL"), nullable=True)

    major = Column(String(100), nullable=False)
    degree_plan = Column(String(100), nullable=True)

    classification = Column(Enum(Classification), nullable=False)
    gpa = Column(DECIMAL(3, 2), nullable=True)
    credits_completed = Column(Integer, default=0)

    status = Column(Enum(AdviseeStatus), default=AdviseeStatus.Active)

    dateCreated = Column(DateTime, default=func.now())
    lastUpdated = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships

