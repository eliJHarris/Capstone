from datetime import datetime
from pydantic import BaseModel


class TermResponse(BaseModel):
    termID: int
    code: str
    startDate: datetime
    endDate: datetime

    class Config:
        from_attributes = True
