from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Schema for creating a new schedule
class notificationCreate(BaseModel):
    notificationID: int = Field(..., description="ID of the notification")
    userID: int = Field(..., description="ID of the user receiving notification")
    description: str = Field(..., description="notification body")

class notificationResponse(BaseModel):
    notificationID: int
    userID: int
    description: str
    createdAt: datetime

    class Config:
        from_attributes = True
