from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, ForeignKey, Text, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

# Define the ENUM type to mirror your SQL CHECK constraint
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
    isActive = Column(Boolean, nullable=False, default=True)
    createdDate = Column(DateTime, nullable=False, default=func.now())

    # Relationship to notifications
    notifications = relationship("Notification", back_populates="user")

class Notification(Base):
    __tablename__ = "notifications"

    notificationID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    userID = Column(Integer, ForeignKey("users.userID"), nullable=False, index=True)
    description = Column(String, nullable=False)
    createdAt = Column(DateTime, nullable=False, default=func.now())

    # Add this line
    user = relationship("User", back_populates="notifications")
