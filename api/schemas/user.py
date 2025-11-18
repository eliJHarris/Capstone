from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

#Describes API Paylods (Request/Response)

class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    ADVISOR = "ADVISOR"
    ADMIN = "ADMIN"


# Schema for creating a new schedule
class UserCreate(BaseModel):
    username: str = Field(..., description="User's username")
    email: str = Field(..., description="User's email")
    role: UserRole = Field(..., description="User's role")
    isActive: int = Field(default=1, description="User's status: 0- inactive 1- active")

# Schema for updating a schedule
class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, description="User's username")
    email: Optional[str] = Field(None, description="User's email")
    isActive: Optional[int] = Field(None, description="User's status: 0- inactive 1- active")

# Schema for schedule response
class UserResponse(BaseModel):
    userID: int
    username: str
    email: str
    role: UserRole
    isActive: int
    createdDate: datetime

    class Config:
        from_attributes = True
