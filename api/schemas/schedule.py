from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

#Describes API Paylods (Request/Response)

class ScheduleStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ScheduleSource(str, Enum):
    USER = "USER"
    ADVISOR = "ADVISOR"
    SYSTEM = "SYSTEM"


# Schema for creating a new schedule
class ScheduleCreate(BaseModel):
    adviseeID: int = Field(..., description="ID of the advisee")
    termID: int = Field(..., description="ID of the term")
    source: ScheduleSource = Field(default=ScheduleSource.USER, description="Source of the schedule")
    status: ScheduleStatus = Field(default=ScheduleStatus.DRAFT, description="Status of the schedule")
    advisorFeedback: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional feedback shared with the advisee about this schedule",
    )


# Schema for updating a schedule
class ScheduleUpdate(BaseModel):
    status: Optional[ScheduleStatus] = Field(None, description="Status of the schedule")
    source: Optional[ScheduleSource] = Field(None, description="Source of the schedule")
    advisorFeedback: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Feedback shared when approving or rejecting",
    )


# Schema for adding a class to a schedule
class AddClassToSchedule(BaseModel):
    sectionID: int = Field(..., description="ID of the section to add")


# Schema for class/section info (nested in response)
class ClassInSchedule(BaseModel):
    classID: int
    sectionID: int
    courseName: str
    courseDescription: Optional[str]
    credits: int
    crn: str
    professorName: Optional[str]
    createdDate: datetime

    class Config:
        from_attributes = True


# Schema for schedule response
class ScheduleResponse(BaseModel):
    scheduleID: int
    adviseeID: int
    termID: int
    termCode: str
    source: ScheduleSource
    status: ScheduleStatus
    createdWhen: datetime
    approvedWhen: Optional[datetime]
    rejectedWhen: Optional[datetime]
    advisorFeedback: Optional[str]
    classes: List[ClassInSchedule] = []

    class Config:
        from_attributes = True


# Schema for schedule list response (without detailed classes)
class ScheduleListResponse(BaseModel):
    scheduleID: int
    adviseeID: int
    termID: int
    termCode: str
    source: ScheduleSource
    status: ScheduleStatus
    createdWhen: datetime
    approvedWhen: Optional[datetime]
    rejectedWhen: Optional[datetime]
    advisorFeedback: Optional[str]
    classCount: int = 0

    class Config:
        from_attributes = True
