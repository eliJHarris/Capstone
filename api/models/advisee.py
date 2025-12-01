from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class AdviseeProfile(Base):
  __tablename__ = "adviseeProfile"

  adviseeID = Column(Integer, primary_key=True, autoincrement=True, index=True)
  userID = Column(Integer, ForeignKey("users.userID"), nullable=False, unique=True)
  advisorID = Column(Integer, nullable=True)
  major = Column(String(100), nullable=False)
  degree_plan = Column(String(100))
  classification = Column(Enum("Freshman", "Sophomore", "Junior", "Senior"), nullable=False)
  gpa = Column(DECIMAL(3, 2))
  credits_completed = Column(Integer, nullable=False, default=0)
  status = Column(Enum("Active", "Inactive", "Graduated", "Suspended"), nullable=False, default="Active")
  dateCreated = Column(DateTime, nullable=False, server_default=func.now())
  lastUpdated = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
