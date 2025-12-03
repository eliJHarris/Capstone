from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


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


class AdviseeBase(BaseModel):
    userID: int
    advisorID: Optional[int] = None
    major: str
    degree_plan: Optional[str] = None
    classification: Classification
    gpa: Optional[float] = None
    credits_completed: int = 0
    status: AdviseeStatus = AdviseeStatus.Active

    class Config:
        from_attributes = True


class AdviseeCreate(AdviseeBase):
    pass


class AdviseeUpdate(BaseModel):
    advisorID: Optional[int] = None
    major: Optional[str] = None
    degree_plan: Optional[str] = None
    classification: Optional[Classification] = None
    gpa: Optional[float] = None
    credits_completed: Optional[int] = None
    status: Optional[AdviseeStatus] = None


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
        from_attributes = True


class AdviseeListItem(BaseModel):
    adviseeID: int
    userID: int
    name: str
    email: Optional[str]
    advisorName: Optional[str] = None
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
