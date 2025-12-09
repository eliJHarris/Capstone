import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class EnrollmentStatus(str, enum.Enum):
    ENROLLED = "ENROLLED"
    COMPLETED = "COMPLETED"
    DROPPED = "DROPPED"
    WITHDRAWN = "WITHDRAWN"


class Enrollment(Base):
    __tablename__ = "enrollments"

    enrollmentID = Column(Integer, primary_key=True, autoincrement=True, index=True)
    adviseeID = Column(Integer, ForeignKey("adviseeProfile.adviseeID"), nullable=False)
    sectionID = Column(Integer, ForeignKey("sections.sectionID"), nullable=False)
    courseID = Column(Integer, ForeignKey("courses.courseID"), nullable=False)
    status = Column(Enum(EnrollmentStatus), nullable=False, default=EnrollmentStatus.ENROLLED)
    grade = Column(String(8))
    creditsEarned = Column(Integer, nullable=False, default=0)
    attemptedNumber = Column(Integer, nullable=False, default=1)
    createdWhen = Column(DateTime, nullable=False)
    section = relationship("Section", primaryjoin="Enrollment.sectionID == Section.sectionID")
