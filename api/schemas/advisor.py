from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ------------------------------
# Create schema
# ------------------------------
class AdvisorProfileCreate(BaseModel):
    advisorID: int = Field(..., description="ID of the advisor (matches userID)")
    name: str = Field(..., max_length=160, description="Advisor's full name")
    office: Optional[str] = Field(None, max_length=160, description="Advisor office location")


# ------------------------------
# Update schema
# ------------------------------
class AdvisorProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=160, description="Advisor's full name")
    office: Optional[str] = Field(None, max_length=160, description="Advisor office location")


# ------------------------------
# Response schema
# ------------------------------
class AdvisorProfileResponse(BaseModel):
    advisorID: int
    name: str
    office: Optional[str]
    createdWhen: datetime

    class Config:
        from_attributes = True
