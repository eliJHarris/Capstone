from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ScheduleStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ScheduleSource(str, Enum):
    USER = "USER"
    ADVISOR = "ADVISOR"
    SYSTEM = "SYSTEM"


class ScheduleCreate(BaseModel):
    adviseeID: int = Field(..., description="ID of the advisee")
    termID: int = Field(..., description="ID of the term")
    source: ScheduleSource = Field(default=ScheduleSource.USER, description="Source of the schedule")
    status: ScheduleStatus = Field(default=ScheduleStatus.DRAFT, description="Status of the schedule")
    advisorFeedback: Optional[str] = Field(
        default=None, description="Optional advisor feedback explaining schedule decisions"
    )


class ScheduleUpdate(BaseModel):
    status: Optional[ScheduleStatus] = Field(None, description="Status of the schedule")
    source: Optional[ScheduleSource] = Field(None, description="Source of the schedule")
    advisorFeedback: Optional[str] = Field(
        default=None, description="Optional advisor feedback explaining schedule decisions"
    )


class AddClassToSchedule(BaseModel):
    sectionID: int = Field(..., description="ID of the section to add")
    aiAssisted: bool = Field(
        False,
        description="Whether this class was added as part of an AI-generated suggestion",
    )


class ClassInSchedule(BaseModel):
    classID: int
    sectionID: int
    sectionStatus: str
    capacity: int
    enrolled: int
    seatsRemaining: int
    courseName: str
    courseDescription: Optional[str]
    credits: int
    crn: str
    professorName: Optional[str]
    createdDate: datetime

    class Config:
        from_attributes = True


class SectionSearchItem(BaseModel):
    sectionID: int
    crn: str
    courseName: str
    courseDescription: Optional[str]
    professorName: Optional[str]
    credits: int
    capacity: int
    enrolled: int
    seatsRemaining: int
    status: str

class ScheduleResponse(BaseModel):
    scheduleID: int
    adviseeID: int
    adviseeName: Optional[str] = None
    termID: int
    termCode: str
    termName: Optional[str] = None
    source: ScheduleSource
    status: ScheduleStatus
    createdWhen: datetime
    approvedWhen: Optional[datetime]
    rejectedWhen: Optional[datetime]
    advisorFeedback: Optional[str] = None
    classes: List[ClassInSchedule] = []

    class Config:
        from_attributes = True


class ScheduleListResponse(BaseModel):
    scheduleID: int
    adviseeID: int
    adviseeName: Optional[str] = None
    termID: int
    termCode: str
    termName: Optional[str] = None
    source: ScheduleSource
    status: ScheduleStatus
    createdWhen: datetime
    approvedWhen: Optional[datetime]
    rejectedWhen: Optional[datetime]
    classCount: int = 0
    advisorFeedback: Optional[str] = None

    class Config:
        from_attributes = True


class ScheduleSuggestionRequest(BaseModel):
    note: Optional[str] = Field(
        None,
        description="Preference or constraint to include in the suggestion prompt",
    )


class AIScheduleNotificationRequest(BaseModel):
   optionNumber: int = Field(
        ...,
        description="The option number provided by the AI suggestion that was applied",
    )
    courseNames: List[str] = Field(
        default_factory=list,
        description="Names or codes of the courses added by this AI schedule option",
    )


class SuggestedCourse(BaseModel):
    course_code: str
    course_name: Optional[str] = None
    credits: float
    section: Optional[str] = None

    class Config:
        allow_population_by_field_name = True


class SuggestedScheduleOption(BaseModel):
    option_number: int
    courses: List[SuggestedCourse]
    total_credits: float
    rationale: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)

    class Config:
        allow_population_by_field_name = True


class ScheduleSuggestionResponse(BaseModel):
    schedules: List[SuggestedScheduleOption]
    general_recommendations: Optional[str] = None
