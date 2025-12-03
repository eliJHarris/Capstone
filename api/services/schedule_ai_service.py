import json
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session, joinedload

from models.advisee import AdviseeProfile
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
)
from models.user import User
from schemas.schedule import (
    ScheduleSuggestionResponse,
    SuggestedCourse,
    SuggestedScheduleOption,
)
from services.openai_service import OpenAIService


class ScheduleAISuggestionService:
    """Prepare context and call OpenAI for schedule suggestions."""

    def __init__(self, db: Session, openai_service: OpenAIService) -> None:
        self.db = db
        self.openai = openai_service

    def generate(self, schedule_id: int, note: Optional[str] = None) -> ScheduleSuggestionResponse:
        schedule, term = self._load_schedule(schedule_id)
        advisee, user = self._load_advisee(schedule.adviseeID)
        context, requirement, validation = self._load_degree_context(schedule.adviseeID)
        available_courses = self._load_available_sections(schedule.termID)

        prompt = self._build_prompt(
            schedule=schedule,
            term=term,
            advisee=advisee,
            user=user,
            context=context,
            requirement=requirement,
            validation=validation,
            available_courses=available_courses,
            note=note,
        )

        completion = self.openai.chat_completion(
            messages=[
                {"role": "system", "content": "You are an academic advising assistant for AdviseMe."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.25,
        )

        try:
            content = completion.choices[0].message.content or ""
        except (AttributeError, IndexError) as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="OpenAI response did not include any content.",
            ) from exc

        return self._parse_response(content)

    def _load_schedule(self, schedule_id: int) -> tuple[Schedule, Term]:
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
            term = (
                self.db.query(Term)
                .filter(Term.termID == schedule.termID)
                .first()
            )
        return schedule, term

    def _load_advisee(self, advisee_id: int) -> tuple[Optional[AdviseeProfile], Optional[User]]:
        advisee = (
            self.db.query(AdviseeProfile)
            .filter(AdviseeProfile.adviseeID == advisee_id)
            .first()
        )
        user = None
        if advisee:
            user = (
                self.db.query(User)
                .filter(User.userID == advisee.userID)
                .first()
            )
        return advisee, user

    def _load_degree_context(
        self, advisee_id: int
    ) -> tuple[Optional[AdviseeDegreeContext], Optional[DegreeRequirementSet], Optional[DegreePlanValidation]]:
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
        return context, requirement, validation

    def _load_available_sections(self, term_id: int, limit: int = 40) -> List[Dict[str, Any]]:
        sections = (
            self.db.query(Section)
            .options(joinedload(Section.course))
            .filter(Section.termID == term_id, Section.status == SectionStatusEnum.OPEN)
            .order_by(Section.crn.asc())
            .limit(limit)
            .all()
        )
        results: List[Dict[str, Any]] = []
        for section in sections:
            course: Optional[Course] = section.course
            status_value = section.status.value if hasattr(section.status, "value") else str(section.status)
            seats_remaining = max((section.capacity or 0) - (section.enrolled or 0), 0)
            if seats_remaining <= 0:
                # Skip sections that are already full to avoid unusable suggestions
                continue
            results.append(
                {
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
                }
            )
        return results

    @staticmethod
    def _build_remaining_requirements(
        requirement: Optional[DegreeRequirementSet],
        context: Optional[AdviseeDegreeContext],
        validation: Optional[DegreePlanValidation],
    ) -> List[Dict[str, Any]]:
        if not requirement:
            return []

        completed = context.completedCourses if context and context.completedCourses else []
        completed_codes = {str(course.get("code", "")).upper() for course in completed}
        remaining: List[Dict[str, Any]] = []

        for group in requirement.requirementData or []:
            missing_courses: List[str] = []
            for course in group.get("courses") or []:
                code = str(course.get("code") or course.get("courseCode") or "").upper()
                if code and code not in completed_codes:
                    missing_courses.append(code)
            remaining.append(
                {
                    "id": group.get("id") or group.get("title"),
                    "title": group.get("title") or "Requirement",
                    "requiredCredits": group.get("requiredCredits")
                    or group.get("required_credits"),
                    "missingCourses": missing_courses,
                }
            )

        if validation and validation.issues:
            for issue in validation.issues:
                remaining.append(
                    {
                        "title": issue.get("message") or "Outstanding requirement",
                        "missingCourses": issue.get("missingCourses") or [],
                    }
                )

        return remaining

    def _build_prompt(
        self,
        *,
        schedule: Schedule,
        term: Optional[Term],
        advisee: Optional[AdviseeProfile],
        user: Optional[User],
        context: Optional[AdviseeDegreeContext],
        requirement: Optional[DegreeRequirementSet],
        validation: Optional[DegreePlanValidation],
        available_courses: List[Dict[str, Any]],
        note: Optional[str],
    ) -> str:
        completed_courses = context.completedCourses if context and context.completedCourses else []
        current_classes = []
        for cls in getattr(schedule, "classes", []) or []:
            section = cls.section
            course = section.course if section else None
            seats_remaining = (
                max((section.capacity or 0) - (section.enrolled or 0), 0) if section else None
            )
            current_classes.append(
                {
                    "class_id": cls.classID,
                    "section_id": getattr(cls, "sectionID", None),
                    "course_code": course.courseName if course else None,
                    "course_name": course.courseName if course else None,
                    "credits": course.credits if course else None,
                    "crn": section.crn if section else None,
                    "seats_remaining": seats_remaining,
                }
            )
        remaining_requirements = self._build_remaining_requirements(requirement, context, validation)

        payload = {
            "student_id": schedule.adviseeID,
            "student_name": user.username if user else None,
            "major": advisee.major if advisee else "Undeclared",
            "semester": term.code if term else str(schedule.termID),
            "completed_courses": completed_courses,
            "current_schedule": current_classes,
            "remaining_requirements": remaining_requirements,
            "available_courses": available_courses,
            "prerequisites": [],
            "preference_note": note or "",
        }

        prompt = (
            "You are an academic advising assistant for AdviseMe.\n"
            f"Student : {payload['student_id']} ({payload['student_name'] or 'student'}) , "
            f"Major : {payload['major']} , Semester : {payload['semester']}\n"
            f"Completed : {json.dumps(payload['completed_courses'], default=str)}\n"
            f"Current Schedule Classes : {json.dumps(payload['current_schedule'], default=str)}\n"
            f"Remaining Requirements : {json.dumps(payload['remaining_requirements'], default=str)}\n"
            f"Available Courses : {json.dumps(payload['available_courses'], default=str)}\n"
            "Prerequisites : []\n"
            "Generate 3 valid schedules (12 -15 credits each). "
            "Use only the section_id values from Available Courses when suggesting sections. "
            "Rules: Option 1 and Option 2 must KEEP the existing classes (current schedule) and add new sections to reach 12-15 credits. "
            "Option 3 must IGNORE existing classes and propose a fresh schedule. "
            "If the current schedule already satisfies credits and requirements, you may make one option simply 'keep current schedule' without adding new sections. "
            "Return as JSON with structure : "
            '{"schedules":[{"option_number":1,"courses":[{"course_code":"...","course_name":"...",'
            '"credits":3,"section":"section_id"}],"total_credits":12,"rationale":"...","warnings":["..."]}],'
            '"general_recommendations":"..."} '
            "Do not include any text outside the JSON object. "
        )

        if note:
            prompt += f"Student preference: {note}. "

        prompt += "Keep courses balanced across requirements and warn about capacity or prerequisite gaps."
        return prompt

    def _parse_response(self, content: str) -> ScheduleSuggestionResponse:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="OpenAI response was not valid JSON.",
            ) from exc

        normalized = self._normalize_response(payload)
        try:
            return ScheduleSuggestionResponse(**normalized)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="OpenAI response was missing required schedule suggestion fields.",
            ) from exc

    def _normalize_response(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raw_options = payload.get("schedules") or payload.get("options") or payload.get("schedule_options") or []
        options: List[SuggestedScheduleOption] = []
        for idx, item in enumerate(raw_options, start=1):
            normalized = self._normalize_option(item, idx)
            if normalized:
                options.append(normalized)

        return {
            "schedules": options,
            "general_recommendations": payload.get("general_recommendations")
            or payload.get("recommendations")
            or payload.get("notes"),
        }

    def _normalize_option(self, item: Dict[str, Any], fallback_index: int) -> Optional[Dict[str, Any]]:
        if not isinstance(item, dict):
            return None

        courses_raw = item.get("courses") or []
        courses: List[SuggestedCourse] = []
        for course in courses_raw:
            normalized_course = self._normalize_course(course)
            if normalized_course:
                courses.append(normalized_course)

        total_credits = item.get("total_credits") or item.get("totalCredits")
        if total_credits is None and courses:
            total_credits = sum(course.credits for course in courses if course.credits is not None)

        warnings = item.get("warnings") or []
        if isinstance(warnings, str):
            warnings = [warnings]

        return {
            "option_number": item.get("option_number")
            or item.get("optionNumber")
            or item.get("number")
            or fallback_index,
            "courses": courses,
            "total_credits": float(total_credits) if total_credits is not None else 0.0,
            "rationale": item.get("rationale") or item.get("reason") or "",
            "warnings": warnings,
        }

    @staticmethod
    def _normalize_course(course: Dict[str, Any]) -> Optional[SuggestedCourse]:
        if not isinstance(course, dict):
            return None

        course_code = (
            course.get("course_code")
            or course.get("courseCode")
            or course.get("code")
            or course.get("course")
        )
        course_name = course.get("course_name") or course.get("courseName") or course.get("name")
        credits_raw = course.get("credits") or 0
        try:
            credits = float(credits_raw)
        except (TypeError, ValueError):
            credits = 0.0

        section = (
            course.get("section")
            or course.get("section_id")
            or course.get("sectionID")
            or course.get("crn")
        )

        normalized = {
            "course_code": course_code or course_name or "Course",
            "course_name": course_name or course_code,
            "credits": credits,
            "section": str(section) if section is not None else None,
        }
        return SuggestedCourse(**normalized)
