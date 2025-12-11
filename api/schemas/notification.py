from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class notificationCreate(BaseModel):
    userID: int = Field(..., description="ID of the user receiving notification")
    description: str = Field(..., description="notification body")
    isRead: bool = Field(default=False, description="Whether the notification has been read")

class notificationResponse(BaseModel):
    notificationID: int
    userID: int
    description: str
    isRead: bool
    createdAt: datetime

    class Config:
        from_attributes = True


class NotificationUpdate(BaseModel):
    isRead: bool = Field(..., description="Read status of the notification")
