import json
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from models.advisee import AdviseeProfile
from models.advisor import AdvisorProfile
from models.degree_plan import (
    AdviseeDegreeContext,
    DegreePlanValidation,
    DegreeRequirementSet,
)
from models.schedule import (
    Class,
    Course,
    Schedule,
    Section,
    SectionStatusEnum,
    Term,
    CoursePrerequisite,
)
from models.enrollment import Enrollment, EnrollmentStatus
from models.user import User
from services.schedule_ai_service import ScheduleAISuggestionService


class ChatContextService:
    """Gather rich advising context to ground chatbot responses."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _safe_enum_value(value: Any) -> Any:
        return value.value if hasattr(value, "value") else value

    def build_context(
        self, advisee_id: Optional[int] = None, schedule_id: Optional[int] = None
    ) -> Dict[str, Any]:
        schedule: Optional[Schedule] = None
        term: Optional[Term] = None

        if schedule_id:
            schedule, term = self._load_schedule(schedule_id)
            advisee_id = advisee_id or schedule.adviseeID

        advisee: Optional[AdviseeProfile] = None
        user: Optional[User] = None
        advisor: Optional[AdvisorProfile] = None
        if advisee_id:
            advisee, user, advisor = self._load_advisee(advisee_id)

        context: Optional[AdviseeDegreeContext] = None
        requirement: Optional[DegreeRequirementSet] = None
        validation: Optional[DegreePlanValidation] = None
        if advisee_id:
            context, requirement, validation = self._load_degree_context(advisee_id)

        available_courses: List[Dict[str, Any]] = []
        blocked_prerequisites: List[Dict[str, Any]] = []
        if schedule:
            available_courses, blocked_prerequisites = self._load_available_sections(
                term.termID if term else schedule.termID,
                advisee_id=advisee_id,
                limit=50,
            )

        current_schedule = self._serialize_current_schedule(schedule)
        remaining_requirements = ScheduleAISuggestionService._build_remaining_requirements(
            requirement=requirement,
            context=context,
            validation=validation,
        )

        return {
            "student": {
                "advisee_id": advisee.adviseeID if advisee else advisee_id,
                "student_name": user.username if user else None,
                "student_email": user.email if user else None,
                "major": advisee.major if advisee else None,
                "degree_plan": advisee.degree_plan if advisee else None,
                "classification": self._safe_enum_value(advisee.classification) if advisee and advisee.classification else None,
                "gpa": float(advisee.gpa) if advisee and advisee.gpa is not None else None,
                "credits_completed": advisee.credits_completed if advisee else None,
                "status": self._safe_enum_value(advisee.status) if advisee and advisee.status else None,
            },
            "advisor": {
                "advisor_id": advisor.advisorID if advisor else None,
                "name": advisor.name if advisor else None,
                "office": advisor.office if advisor else None,
            }
            if advisor
            else None,
            "term": {
                "term_id": term.termID if term else schedule.termID if schedule else None,
                "code": term.code if term else None,
                "start": term.startDate if term else None,
                "end": term.endDate if term else None,
            }
            if term or schedule
            else None,
            "schedule": {
                "schedule_id": schedule.scheduleID if schedule else None,
                "status": self._safe_enum_value(schedule.status) if schedule else None,
                "source": self._safe_enum_value(schedule.source) if schedule else None,
                "current_classes": current_schedule,
            },
            "degree_context": {
                "requirement_metadata": {
                    "program_code": requirement.programCode if requirement else None,
                    "program_name": requirement.programName if requirement else None,
                    "catalog_year": requirement.catalogYear if requirement else None,
                    "total_credits": requirement.totalCredits if requirement else None,
                },
                "completed_courses": context.completedCourses if context and context.completedCourses else [],
                "context_overrides": context.overrides if context else None,
                "context_notes": context.notes if context else None,
                "remaining_requirements": remaining_requirements,
            },
            "validation": {
                "status": self._safe_enum_value(getattr(validation, "status", None)),
                "completion_percent": getattr(validation, "completionPercent", None),
                "message": getattr(validation, "message", None),
                "issues": getattr(validation, "issues", None) or [],
                "run_type": self._safe_enum_value(getattr(validation, "runType", None)),
                "last_run": getattr(validation, "createdAt", None),
            }
            if validation
            else None,
            "available_courses": available_courses,
            "prerequisite_blocks": blocked_prerequisites,
            "raw_json": json.dumps(
                {
                    "remaining_requirements": remaining_requirements,
                    "available_courses": available_courses,
                    "prerequisite_blocks": blocked_prerequisites,
                },
                default=str,
            ),
        }

    def _load_schedule(self, schedule_id: int) -> Tuple[Schedule, Optional[Term]]:
        schedule = (
            self.db.query(Schedule)
            .options(
                joinedload(Schedule.term),
                joinedload(Schedule.classes)
                .joinedload(Class.section)
                .joinedload(Section.course),
            )
            .filter(Schedule.scheduleID == schedule_id)
            .first()
        )
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found",
            )
        term = schedule.term
        if not term:
            term = self.db.query(Term).filter(Term.termID == schedule.termID).first()
        return schedule, term

    def _load_advisee(
        self, advisee_id: int
    ) -> Tuple[Optional[AdviseeProfile], Optional[User], Optional[AdvisorProfile]]:
        advisee = (
            self.db.query(AdviseeProfile)
            .filter(AdviseeProfile.adviseeID == advisee_id)
            .first()
        )
        user = None
        advisor = None
        if advisee:
            user = (
                self.db.query(User)
                .filter(User.userID == advisee.userID)
                .first()
            )
            if advisee.advisorID:
                advisor = (
                    self.db.query(AdvisorProfile)
                    .filter(AdvisorProfile.advisorID == advisee.advisorID)
                    .first()
                )
        return advisee, user, advisor

    def _load_degree_context(
        self, advisee_id: int
    ) -> Tuple[Optional[AdviseeDegreeContext], Optional[DegreeRequirementSet], Optional[DegreePlanValidation]]:
        context = (
            self.db.query(AdviseeDegreeContext)
            .options(joinedload(AdviseeDegreeContext.requirementSet))
            .filter(AdviseeDegreeContext.adviseeID == advisee_id)
            .first()
        )
        requirement = context.requirementSet if context else None
        validation = (
            self.db.query(DegreePlanValidation)
            .filter(DegreePlanValidation.adviseeID == advisee_id)
            .order_by(DegreePlanValidation.createdAt.desc())
            .first()
        )

        if not requirement:
            advisee = (
                self.db.query(AdviseeProfile)
                .filter(AdviseeProfile.adviseeID == advisee_id)
                .first()
            )
            program_code = None
            if advisee:
                program_code = advisee.degree_plan or advisee.major
            if program_code:
                requirement = (
                    self.db.query(DegreeRequirementSet)
                    .filter(DegreeRequirementSet.programCode == program_code)
                    .order_by(DegreeRequirementSet.createdAt.desc())
                    .first()
                )

        return context, requirement, validation

    def _load_available_sections(
        self, term_id: int, advisee_id: Optional[int] = None, limit: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        sections_query = (
            self.db.query(Section)
            .options(joinedload(Section.course))
            .filter(Section.termID == term_id, Section.status == SectionStatusEnum.OPEN)
            .order_by(Section.crn.asc())
        )
        if limit:
            sections_query = sections_query.limit(limit)
        sections = sections_query.all()
        if not sections:
            return [], []

        completed_course_ids: set[int] = set()
        if advisee_id:
            completed_course_ids = {
                course_id
                for (course_id,) in (
                    self.db.query(Enrollment.courseID)
                    .filter(
                        Enrollment.adviseeID == advisee_id,
                        Enrollment.status == EnrollmentStatus.COMPLETED,
                        Enrollment.creditsEarned > 0,
                    )
                    .all()
                )
            }

        course_ids = {section.courseID for section in sections}
        prereq_rows = (
            self.db.query(
                CoursePrerequisite.courseID,
                CoursePrerequisite.prerequisiteCourseID,
                Course.courseName,
            )
            .join(Course, Course.courseID == CoursePrerequisite.prerequisiteCourseID)
            .filter(CoursePrerequisite.courseID.in_(course_ids))
            .all()
        )
        prereq_map: Dict[int, List[tuple[int, str]]] = {}
        for course_id, prereq_id, prereq_name in prereq_rows:
            prereq_map.setdefault(course_id, []).append((prereq_id, prereq_name))

        results: List[Dict[str, Any]] = []
        blocked: List[Dict[str, Any]] = []
        for section in sections:
            course: Optional[Course] = section.course
            status_value = section.status.value if hasattr(section.status, "value") else str(section.status)
            seats_remaining = max((section.capacity or 0) - (section.enrolled or 0), 0)
            if seats_remaining <= 0:
                continue
            prereqs = prereq_map.get(section.courseID, [])
            missing_prereqs: List[str] = []
            if advisee_id:
                missing_prereqs = [
                    name or f"Course {prereq_id}"
                    for prereq_id, name in prereqs
                    if prereq_id not in completed_course_ids
                ]

            entry = {
                "course_id": section.courseID,
                "section_id": section.sectionID,
                "crn": section.crn,
                "course_code": course.courseName if course else f"Course {section.courseID}",
                "course_name": course.courseName if course else "",
                "course_description": course.description if course else "",
                "credits": course.credits if course else None,
                "professor": section.professorName,
                "capacity": section.capacity,
                "enrolled": section.enrolled,
                "seats_remaining": seats_remaining,
                "status": status_value,
                "prerequisites": [name or f"Course {pid}" for pid, name in prereqs],
                "missing_prerequisites": missing_prereqs,
                "prerequisites_met": not missing_prereqs,
            }
            if advisee_id and missing_prereqs:
                blocked.append(entry)
                continue
            results.append(entry)
        return results, blocked

    def _serialize_current_schedule(self, schedule: Optional[Schedule]) -> List[Dict[str, Any]]:
        if not schedule:
            return []

        current_classes: List[Dict[str, Any]] = []
        for cls in getattr(schedule, "classes", []) or []:
            section = cls.section
            course = section.course if section else None
            seats_remaining = (
                max((section.capacity or 0) - (section.enrolled or 0), 0) if section else None
            )
            current_classes.append(
                {
                    "class_id": cls.classID,
                    "course_id": course.courseID if course else None,
                    "section_id": getattr(cls, "sectionID", None),
                    "course_code": course.courseName if course else None,
                    "course_name": course.courseName if course else None,
                    "credits": course.credits if course else None,
                    "crn": section.crn if section else None,
                    "section_status": self._safe_enum_value(section.status) if section else None,
                    "seats_remaining": seats_remaining,
                }
            )
        return current_classes
