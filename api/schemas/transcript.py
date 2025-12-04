from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TranscriptCourse(BaseModel):
    courseCode: str = Field(..., description="Course code, e.g. CS 3213")
    courseTitle: str = Field(..., description="Full course title")
    credits: float = Field(..., description="Credit hours for the course")
    grade: str = Field(..., description="Final grade recorded for the course")
    status: str = Field(..., description="Completion status for the course")
    term: Optional[str] = Field(None, description="Academic term the course belongs to")


class TranscriptTerm(BaseModel):
    term: str = Field(..., description="Academic term label, e.g. Fall 2023")
    termGpa: float = Field(..., description="GPA for the given term")
    creditsAttempted: float = Field(..., description="Attempted credit hours for the term")
    creditsEarned: float = Field(..., description="Completed credit hours for the term")
    courses: List[TranscriptCourse] = Field(default_factory=list)


class TranscriptResponse(BaseModel):
    adviseeID: int
    studentName: str
    username: str
    major: Optional[str] = None
    classification: Optional[str] = None
    catalogYear: Optional[str] = None
    cumulativeGpa: float
    totalCredits: float
    terms: List[TranscriptTerm]
    updatedAt: Optional[datetime] = None

    class Config:
        from_attributes = True
