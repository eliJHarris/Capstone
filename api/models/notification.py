from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Notification(Base):
    __tablename__ = "notifications"

    notificationID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    userID = Column(Integer, ForeignKey("users.userID"), nullable=False, index=True)
    description = Column(String, nullable=False)
    createdAt = Column(DateTime, nullable=False, default=func.now())

    user = relationship("User", back_populates="notifications")
