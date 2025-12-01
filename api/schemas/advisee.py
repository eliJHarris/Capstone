from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AdviseeListItem(BaseModel):
  adviseeID: int
  userID: int
  name: str
  email: Optional[str]
  major: Optional[str]
  degreePlan: Optional[str]
  classification: Optional[str]
  gpa: Optional[float]
  creditsCompleted: Optional[int]
  status: Optional[str]
  advisorID: Optional[int]
  updatedAt: Optional[datetime]

  class Config:
    from_attributes = True
