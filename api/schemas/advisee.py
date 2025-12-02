from pydantic import BaseModel
from typing import Optional
from enum import Enum
from datetime import datetime


class Classification(str, Enum):
    Freshman = "Freshman"
    Sophomore = "Sophomore"
    Junior = "Junior"
    Senior = "Senior"


class AdviseeStatus(str, Enum):
    Active = "Active"
    Inactive = "Inactive"
    Graduated = "Graduated"
    Suspended = "Suspended"


# -----------------------------
# Base Schema
# -----------------------------
class AdviseeBase(BaseModel):
    userID: int
    advisorID: Optional[int] = None
    major: str
    degree_plan: Optional[str] = None
    classification: Classification
    gpa: Optional[float] = None
    credits_completed: int = 0
    status: AdviseeStatus = AdviseeStatus.Active


# -----------------------------
# Create
# -----------------------------
class AdviseeCreate(AdviseeBase):
    pass


# -----------------------------
# Update
# -----------------------------
class AdviseeUpdate(BaseModel):
    advisorID: Optional[int] = None
    major: Optional[str] = None
    degree_plan: Optional[str] = None
    classification: Optional[Classification] = None
    gpa: Optional[float] = None
    credits_completed: Optional[int] = None
    status: Optional[AdviseeStatus] = None


# -----------------------------
# Response
# -----------------------------
class AdviseeResponse(BaseModel):
    adviseeID: int
    userID: int
    advisorID: Optional[int]
    major: str
    degree_plan: Optional[str]
    classification: Classification
    gpa: Optional[float]
    credits_completed: int
    status: AdviseeStatus
    dateCreated: datetime
    lastUpdated: datetime

    class Config:
        orm_mode = True
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AdviseeListItem(BaseModel):
  adviseeID: int
  userID: int
  name: str
  email: Optional[str]
  major: Optional[str]
  degreePlan: Optional[str]
  classification: Optional[str]
  gpa: Optional[float]
  creditsCompleted: Optional[int]
  status: Optional[str]
  advisorID: Optional[int]
  updatedAt: Optional[datetime]

  class Config:
    from_attributes = True
