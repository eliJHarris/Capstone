from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class RequirementCourse(BaseModel):
    code: str = Field(..., description="Course code such as ENG 1013")
    title: Optional[str] = Field(None, description="Human-readable course title")
    credits: float = Field(..., description="Credit hours for the course")


class RequirementGroup(BaseModel):
    id: Optional[str] = Field(None, description="Identifier for the requirement group")
    title: str = Field(..., description="Display name for the group")
    requiredCredits: float = Field(..., description="Credits required for this group")
    courses: List[RequirementCourse] = Field(default_factory=list)
    description: Optional[str] = None


class DegreeRequirementSetBase(BaseModel):
    programCode: str
    catalogYear: str
    programName: str
    totalCredits: float = Field(..., gt=0)
    requirementGroups: List[RequirementGroup] = Field(default_factory=list)
    sourceDocument: Optional[str] = None


class DegreeRequirementSetCreate(DegreeRequirementSetBase):
    pass


class DegreeRequirementSetResponse(DegreeRequirementSetBase):
    requirementSetID: int
    requirementGroups: List[RequirementGroup] = Field(default_factory=list, alias="requirementData")
    createdAt: datetime
    updatedAt: datetime

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


class CompletedCourse(BaseModel):
    code: str
    title: Optional[str] = None
    credits: float = Field(..., gt=0)
    term: Optional[str] = None
    status: Optional[str] = Field("COMPLETED", description="Status flag, default COMPLETED")


class AdviseeContextUpsert(BaseModel):
    requirementSetID: int
    completedCourses: List[CompletedCourse] = Field(default_factory=list)
    overrides: Optional[dict] = None
    notes: Optional[str] = None


class AdviseeContextResponse(BaseModel):
    contextID: int
    adviseeID: int
    requirementSetID: int
    completedCourses: List[CompletedCourse]
    overrides: Optional[dict]
    notes: Optional[str]
    updatedAt: datetime

    class Config:
        orm_mode = True


class ValidationStatusEnum(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"


class ValidationRunTypeEnum(str, Enum):
    MANUAL = "MANUAL"
    AUTOMATIC = "AUTOMATIC"


class ValidationIssue(BaseModel):
    requirementId: Optional[str] = None
    message: str
    missingCourses: List[str] = Field(default_factory=list)


class DegreePlanValidationResponse(BaseModel):
    validationID: int
    adviseeID: int
    requirementSetID: Optional[int]
    status: ValidationStatusEnum
    runType: ValidationRunTypeEnum
    completionPercent: float
    issues: List[ValidationIssue] = Field(default_factory=list)
    message: Optional[str] = None
    triggeredBy: Optional[int] = None
    createdAt: datetime
    updatedAt: datetime
    startedAt: Optional[datetime] = None
    finishedAt: Optional[datetime] = None

    class Config:
        orm_mode = True


class ValidationRequest(BaseModel):
    triggeredBy: Optional[int] = Field(None, description="User ID that triggered the validation")


class AdviseePlanSummary(BaseModel):
    context: Optional[AdviseeContextResponse]
    requirementSet: Optional[DegreeRequirementSetResponse]
    latestValidation: Optional[DegreePlanValidationResponse]
