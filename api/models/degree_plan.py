from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import JSON as MySQLJSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from .base import Base


class ValidationStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"


class ValidationRunType(str, enum.Enum):
    MANUAL = "MANUAL"
    AUTOMATIC = "AUTOMATIC"


class DegreeRequirementSet(Base):
    __tablename__ = "degree_requirement_sets"

    requirementSetID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    programCode = Column(String(64), nullable=False, index=True)
    catalogYear = Column(String(32), nullable=False, index=True)
    programName = Column(String(255), nullable=False)
    totalCredits = Column(Integer, nullable=False, default=120)
    requirementData = Column(MySQLJSON, nullable=False)
    sourceDocument = Column(String(255))
    createdAt = Column(DateTime, nullable=False, server_default=func.now())
    updatedAt = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    contexts = relationship("AdviseeDegreeContext", back_populates="requirementSet")
    validations = relationship("DegreePlanValidation", back_populates="requirementSet")


class AdviseeDegreeContext(Base):
    __tablename__ = "advisee_degree_context"

    contextID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    adviseeID = Column(Integer, nullable=False, index=True, unique=True)
    requirementSetID = Column(
        Integer,
        ForeignKey("degree_requirement_sets.requirementSetID"),
        nullable=False,
    )
    completedCourses = Column(MySQLJSON, nullable=False, default=list)
    overrides = Column(MySQLJSON, nullable=True)
    notes = Column(Text)
    updatedAt = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    createdAt = Column(DateTime, nullable=False, server_default=func.now())

    requirementSet = relationship("DegreeRequirementSet", back_populates="contexts")
    validations = relationship(
        "DegreePlanValidation",
        back_populates="context",
        cascade="all, delete-orphan",
    )


class DegreePlanValidation(Base):
    __tablename__ = "degree_plan_validations"

    validationID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    adviseeID = Column(Integer, nullable=False, index=True)
    contextID = Column(
        Integer,
        ForeignKey("advisee_degree_context.contextID"),
        nullable=True,
    )
    requirementSetID = Column(
        Integer,
        ForeignKey("degree_requirement_sets.requirementSetID"),
        nullable=True,
    )
    status = Column(
        Enum(ValidationStatus),
        nullable=False,
        default=ValidationStatus.PENDING,
    )
    runType = Column(
        Enum(ValidationRunType),
        nullable=False,
        default=ValidationRunType.MANUAL,
    )
    completionPercent = Column(Float, nullable=False, default=0.0)
    issues = Column(MySQLJSON, nullable=True)
    llmCourseBreakdown = Column(MySQLJSON, nullable=True)
    message = Column(String(255))
    triggeredBy = Column(Integer, nullable=True)
    startedAt = Column(DateTime)
    finishedAt = Column(DateTime)
    createdAt = Column(DateTime, nullable=False, server_default=func.now())
    updatedAt = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    requirementSet = relationship("DegreeRequirementSet", back_populates="validations")
    context = relationship("AdviseeDegreeContext", back_populates="validations")
