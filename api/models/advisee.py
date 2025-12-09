import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, case, select
from sqlalchemy.orm import column_property
from sqlalchemy.sql import func

from .base import Base
from .enrollment import Enrollment, EnrollmentStatus
from .schedule import Course

GRADE_POINTS = {
    "A": 4.0,
    "A-": 3.7,
    "B+": 3.3,
    "B": 3.0,
    "B-": 2.7,
    "C+": 2.3,
    "C": 2.0,
    "C-": 1.7,
    "D": 1.0,
    "F": 0.0,
}


def _build_gpa_subquery(advisee_id_column):
    grade_value = func.upper(func.trim(func.coalesce(Enrollment.grade, "")))
    credit_value = func.coalesce(Course.credits, 0)

    grade_point_conditions = tuple(
        (grade_value == grade, points) for grade, points in GRADE_POINTS.items()
    )
    credit_conditions = tuple(
        (grade_value == grade, credit_value) for grade in GRADE_POINTS.keys()
    )

    grade_point_case = case(*grade_point_conditions, else_=None) if grade_point_conditions else case(else_=None)
    credit_case = case(*credit_conditions, else_=0) if credit_conditions else case(else_=0)

    numerator = func.sum(grade_point_case * credit_value)
    denominator = func.sum(credit_case)
    gpa_value = func.round(numerator / func.nullif(denominator, 0), 2)

    join_stmt = Enrollment.__table__.join(Course.__table__, Enrollment.courseID == Course.courseID)
    return (
        select(gpa_value)
        .select_from(join_stmt)
        .where(
            Enrollment.adviseeID == advisee_id_column,
            Enrollment.status == EnrollmentStatus.COMPLETED,
        )
        .correlate_except(Enrollment)
        .scalar_subquery()
    )


class Classification(str, enum.Enum):
    Freshman = "Freshman"
    Sophomore = "Sophomore"
    Junior = "Junior"
    Senior = "Senior"


class AdviseeStatus(str, enum.Enum):
    Active = "Active"
    Inactive = "Inactive"
    Graduated = "Graduated"
    Suspended = "Suspended"


class AdviseeProfile(Base):
    __tablename__ = "adviseeProfile"

    adviseeID = Column(Integer, primary_key=True, autoincrement=True, index=True)
    userID = Column(Integer, ForeignKey("users.userID", ondelete="CASCADE"), nullable=False, unique=True)
    advisorID = Column(Integer, ForeignKey("advisorProfile.advisorID", ondelete="SET NULL"), nullable=True)
    # Stored as program code; column name in DB is majorCode
    major = Column("majorCode", String(64), ForeignKey("majors.programCode", ondelete="RESTRICT"), nullable=False)
    degree_plan = Column(String(100))
    classification = Column(Enum(Classification), nullable=False)
    gpa = column_property(_build_gpa_subquery(adviseeID))
    credits_completed = Column(Integer, nullable=False, default=0)
    status = Column(Enum(AdviseeStatus), nullable=False, default=AdviseeStatus.Active)
    dateCreated = Column(DateTime, nullable=False, server_default=func.now())
    lastUpdated = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
