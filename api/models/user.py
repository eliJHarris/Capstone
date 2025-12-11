from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, ForeignKey, Text, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from .base import Base

class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    ADVISOR = "ADVISOR"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = "users"

    userID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    isActive = Column(Integer, nullable=False, default=True)
    createdDate = Column(DateTime, nullable=False, default=func.now())
    notifications = relationship("Notification", back_populates="user")
