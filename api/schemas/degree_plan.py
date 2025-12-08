from datetime import datetime
from enum import Enum
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from schemas.advisee import AdviseeResponse
from schemas.transcript import TranscriptResponse


class PrerequisiteClause(BaseModel):
    type: Literal["PREREQUISITE", "COREQUISITE", "PREREQ_OR_CONCURRENT"] = "PREREQUISITE"
    options: List[List[str]] = Field(
        default_factory=list,
        description="Each nested list represents a set of course codes that must all be satisfied; collections are treated as OR options.",
    )
    text: Optional[str] = Field(None, description="Original catalog snippet for reference.")


class RequirementCourse(BaseModel):
    code: str = Field(..., description="Course code such as ENG 1013")
    title: Optional[str] = Field(None, description="Human-readable course title")
    credits: float = Field(..., description="Credit hours for the course")
    prerequisites: List[PrerequisiteClause] = Field(default_factory=list)


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
        from_attributes = True
        validate_by_name = True


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
        from_attributes = True


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
    severity: Optional[str] = Field("ERROR", description="ERROR or WARNING")
    category: Optional[str] = Field(None, description="Optional classifier such as PREREQUISITE")


class LLMCourseBreakdown(BaseModel):
    takenCourses: List[str] = Field(default_factory=list)
    neededCourses: List[str] = Field(default_factory=list)


class ConcentrationOption(BaseModel):
    name: str
    requiredHours: float
    completedHours: float
    remainingHours: float
    satisfied: bool
    takenCourses: List[str] = Field(default_factory=list)
    missingCourses: List[str] = Field(default_factory=list)


class ConcentrationSummary(BaseModel):
    groupId: Optional[str] = None
    title: Optional[str] = None
    requiredSelections: int
    satisfiedSelections: int
    options: List[ConcentrationOption] = Field(default_factory=list)


class GeneralEducationSummary(BaseModel):
    groupId: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    requiredSelections: int
    satisfiedSelections: int
    remainingSelections: int
    takenCourses: List[str] = Field(default_factory=list)
    remainingCourses: List[str] = Field(default_factory=list)


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
    warnings: List[ValidationIssue] = Field(default_factory=list)
    concentrations: List[ConcentrationSummary] = Field(default_factory=list)
    minors: List[ConcentrationSummary] = Field(default_factory=list)
    concentrationIssues: List[ValidationIssue] = Field(default_factory=list)
    minorIssues: List[ValidationIssue] = Field(default_factory=list)
    concentrationRequirementCount: int = 0
    concentrationSatisfiedCount: int = 0
    concentrationCompletionPercent: float = 0.0
    minorRequirementCount: int = 0
    minorSatisfiedCount: int = 0
    minorCompletionPercent: float = 0.0
    generalEducation: List[GeneralEducationSummary] = Field(default_factory=list)
    generalEducationRequirementCount: int = 0
    generalEducationSatisfiedCount: int = 0
    generalEducationCompletionPercent: float = 0.0
    majorRequirementCount: int = 0
    majorSatisfiedCount: int = 0
    majorCompletionPercent: float = 0.0
    llmCourseBreakdown: Optional[LLMCourseBreakdown] = None

    class Config:
        from_attributes = True
        validate_by_name = True


class ValidationRequest(BaseModel):
    triggeredBy: Optional[int] = Field(None, description="User ID that triggered the validation")


class AdviseePlanSummary(BaseModel):
    context: Optional[AdviseeContextResponse]
    requirementSet: Optional[DegreeRequirementSetResponse]
    latestValidation: Optional[DegreePlanValidationResponse]
    student: Optional[AdviseeResponse] = None
    transcript: Optional[TranscriptResponse] = None
