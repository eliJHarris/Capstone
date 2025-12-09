from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    STUDENT = "STUDENT"
    ADVISOR = "ADVISOR"
    ADMIN = "ADMIN"

class UserCreate(BaseModel):
    username: str = Field(..., description="User's username")
    email: str = Field(..., description="User's email")
    role: UserRole = Field(..., description="User's role")
    isActive: int = Field(default=1, description="User's status: 0- inactive 1- active")

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, description="User's username")
    email: Optional[str] = Field(None, description="User's email")
    isActive: Optional[int] = Field(None, description="User's status: 0- inactive 1- active")

class UserResponse(BaseModel):
    userID: int
    username: str
    email: str
    role: UserRole
    isActive: int
    createdDate: datetime

    class Config:
        from_attributes = True
