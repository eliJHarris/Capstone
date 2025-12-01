from sqlalchemy import (
  Column,
  Integer,
  String,
  DateTime,
  Text,
  Enum,
  ForeignKey,
  DECIMAL,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum


Base = declarative_base()


class ValidationStatus(str, enum.Enum):
  PENDING = "PENDING"
  RUNNING = "RUNNING"
  PASSED = "PASSED"
  FAILED = "FAILED"
  ERROR = "ERROR"


class RunType(str, enum.Enum):
  MANUAL = "MANUAL"
  AUTOMATIC = "AUTOMATIC"


class DegreeRequirementSet(Base):
  __tablename__ = "degree_requirement_sets"

  requirementSetID = Column(Integer, primary_key=True, index=True, autoincrement=True)
  programCode = Column(String(64), nullable=False)
  catalogYear = Column(String(32), nullable=False)
  programName = Column(String(255), nullable=False)
  totalCredits = Column(Integer, default=120)
  requirementData = Column(JSON, nullable=False)
  sourceDocument = Column(String(255))
  createdAt = Column(DateTime)
  updatedAt = Column(DateTime)


class AdviseeDegreeContext(Base):
  __tablename__ = "advisee_degree_context"

  contextID = Column(Integer, primary_key=True, index=True, autoincrement=True)
  adviseeID = Column(Integer, unique=True, nullable=False)
  requirementSetID = Column(
    Integer,
    ForeignKey("degree_requirement_sets.requirementSetID"),
    nullable=False,
  )

  requirementSet = relationship("DegreeRequirementSet")
  completedCourses = Column(JSON, nullable=False)
  overrides = Column(JSON)
  notes = Column(Text)
  createdAt = Column(DateTime)
  updatedAt = Column(DateTime)


class DegreePlanValidation(Base):
  __tablename__ = "degree_plan_validations"

  validationID = Column(Integer, primary_key=True, index=True, autoincrement=True)
  adviseeID = Column(Integer, index=True, nullable=False)
  contextID = Column(Integer, ForeignKey("advisee_degree_context.contextID"))
  requirementSetID = Column(Integer, ForeignKey("degree_requirement_sets.requirementSetID"))

  status = Column(Enum(ValidationStatus), default=ValidationStatus.PENDING)
  runType = Column(Enum(RunType), default=RunType.MANUAL)
  completionPercent = Column(DECIMAL(5, 2), default=0)
  issues = Column(JSON)
  message = Column(String(255))
  triggeredBy = Column(Integer, nullable=True)

  startedAt = Column(DateTime)
  finishedAt = Column(DateTime)
  createdAt = Column(DateTime)
  updatedAt = Column(DateTime)

  requirementSet = relationship("DegreeRequirementSet")
  context = relationship("AdviseeDegreeContext")
