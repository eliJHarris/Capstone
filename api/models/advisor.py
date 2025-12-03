from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from .base import Base

class AdvisorProfile(Base):
    __tablename__ = "advisorProfile"

    advisorID = Column(Integer, ForeignKey("users.userID"), primary_key=True, index=True)
    name = Column(String(160), nullable=False)
    office = Column(String(160), nullable=True)
    createdWhen = Column(DateTime, nullable=False, server_default=func.now())
