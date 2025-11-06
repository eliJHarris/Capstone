from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

class Notification(Base):
    __tablename__ = "notifications"

    notificationID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    userID = Column(Integer, ForeignKey("users.userID"), nullable=False, index=True)
    description = Column(String, nullable=False)
    createdAt = Column(DateTime, nullable=False, default=func.now())
