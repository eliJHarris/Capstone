from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, ForeignKey, Text, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from .base import Base

#Describes database entities. Represents how data is stored and loaded.

class ScheduleStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ScheduleSourceEnum(str, enum.Enum):
    USER = "USER"
    ADVISOR = "ADVISOR"
    SYSTEM = "SYSTEM"


class SectionStatusEnum(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class Term(Base):
    __tablename__ = "terms"

    termID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(32), nullable=False, unique=True)
    startDate = Column(DateTime, nullable=False)
    endDate = Column(DateTime, nullable=False)

    # Relationships
    schedules = relationship("Schedule", back_populates="term")
    sections = relationship("Section", back_populates="term")


class Course(Base):
    __tablename__ = "courses"

    courseID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    courseName = Column(String(160), nullable=False)
    description = Column(Text)
    credits = Column(Integer, nullable=False)

    # Relationships
    sections = relationship("Section", back_populates="course")


class Section(Base):
    __tablename__ = "sections"

    sectionID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    courseID = Column(Integer, ForeignKey("courses.courseID"), nullable=False)
    termID = Column(Integer, ForeignKey("terms.termID"), nullable=False)
    crn = Column(String(32), nullable=False, unique=True)
    capacity = Column(Integer, nullable=False)
    enrolled = Column(Integer, nullable=False, default=0)
    professorName = Column(String(160))
    status = Column(Enum(SectionStatusEnum), nullable=False, default=SectionStatusEnum.OPEN)
    description = Column(Text)

    # Relationships
    course = relationship("Course", back_populates="sections")
    term = relationship("Term", back_populates="sections")
    classes = relationship("Class", back_populates="section")


class Schedule(Base):
    __tablename__ = "schedules"

    scheduleID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    adviseeID = Column(Integer, nullable=False, index=True)
    termID = Column(Integer, ForeignKey("terms.termID"), nullable=False)
    source = Column(Enum(ScheduleSourceEnum), nullable=False, default=ScheduleSourceEnum.USER)
    status = Column(Enum(ScheduleStatusEnum), nullable=False, default=ScheduleStatusEnum.DRAFT)
    createdWhen = Column(DateTime, nullable=False)
    approvedWhen = Column(DateTime)
    rejectedWhen = Column(DateTime)

    # Relationships
    term = relationship("Term", back_populates="schedules")
    classes = relationship("Class", back_populates="schedule", cascade="all, delete-orphan")


class Class(Base):
    __tablename__ = "classes"

    classID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sectionID = Column(Integer, ForeignKey("sections.sectionID"), nullable=False)
    scheduleID = Column(Integer, ForeignKey("schedules.scheduleID"), nullable=False)
    termID = Column(Integer, nullable=False)
    createdDate = Column(DateTime, nullable=False)

    # Relationships
    section = relationship("Section", back_populates="classes")
    schedule = relationship("Schedule", back_populates="classes")
