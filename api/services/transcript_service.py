from datetime import datetime
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.advisee import AdviseeProfile
from models.enrollment import Enrollment, EnrollmentStatus
from models.schedule import Course, Section, Term
from models.user import User
from schemas.transcript import TranscriptCourse, TranscriptResponse, TranscriptTerm


class TranscriptService:
    """
    Transcript generator that uses real enrollment data.

    Role rules:
    - Students/advisees can only view their own transcript
    - Advisors and admins can view any advisee
    """

    GRADE_POINTS: Dict[str, float] = {
        "A": 4.0,
        "B": 3.0,
        "C": 2.0,
        "D": 1.0,
        "F": 0.0,
    }

    @classmethod
    def normalize_role(cls, role: Optional[str]) -> str:
        if not role:
            return "student"
        normalized = role.strip().lower()
        if normalized == "advisee":
            return "student"
        return normalized

    @classmethod
    def _load_advisee(cls, db: Session, advisee_id: int) -> Tuple[AdviseeProfile, User]:
        result = (
            db.query(AdviseeProfile, User)
            .join(User, User.userID == AdviseeProfile.userID)
            .filter(AdviseeProfile.adviseeID == advisee_id)
            .first()
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Advisee profile not found",
            )
        return result

    @classmethod
    def _resolve_advisee_for_user(cls, db: Session, username: str) -> Optional[AdviseeProfile]:
        username = (username or "").strip()
        if not username:
            return None
        match = (
            db.query(AdviseeProfile, User)
            .join(User, User.userID == AdviseeProfile.userID)
            .filter(User.username == username)
            .first()
        )
        if not match:
            return None
        profile, _ = match
        return profile

    @classmethod
    def _ensure_student_access(cls, db: Session, advisee_id: int, user_claims: Dict) -> None:
        username = (
            user_claims.get("uid")
            or user_claims.get("sub")
            or user_claims.get("cn")
            or ""
        )
        username = str(username).strip()
        profile = cls._resolve_advisee_for_user(db, username)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No advisee profile associated with this account",
            )
        if profile.adviseeID != advisee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students can only view their own transcripts",
            )

    @classmethod
    def _compute_term(cls, raw_term: Dict) -> TranscriptTerm:
        courses: List[TranscriptCourse] = []
        for course in raw_term.get("courses", []):
            courses.append(
                TranscriptCourse(
                    courseCode=course["courseCode"],
                    courseTitle=course["courseTitle"],
                    credits=course["credits"],
                    grade=course["grade"],
                    status="Completed" if course["grade"] not in {"IP", "In Progress"} else "In Progress",
                    term=raw_term.get("term"),
                )
            )

        attempted = sum(course.credits for course in courses if course.grade not in {"IP", "In Progress"})
        earned = sum(course.credits for course in courses if course.grade not in {"F", "IP", "In Progress"})
        term_gpa = cls._calculate_gpa(courses)

        return TranscriptTerm(
            term=raw_term.get("term", "N/A"),
            termGpa=term_gpa,
            creditsAttempted=attempted,
            creditsEarned=earned,
            courses=courses,
        )

    @classmethod
    def _calculate_gpa(cls, courses: List[TranscriptCourse]) -> float:
        total_points = 0.0
        total_credits = 0.0
        for course in courses:
            points = cls.GRADE_POINTS.get(course.grade)
            if points is None:
                continue
            total_points += points * course.credits
            total_credits += course.credits
        if total_credits == 0:
            return 0.0
        return round(total_points / total_credits, 2)

    @classmethod
    @classmethod
    def _normalize_grade(cls, grade: Optional[str], status_value: Optional[EnrollmentStatus]) -> str:
        grade = (grade or "").strip().upper()
        try:
            status_value = EnrollmentStatus(status_value) if status_value is not None else None
        except ValueError:
            status_value = None

        if grade:
            return grade
        if status_value in {EnrollmentStatus.ENROLLED}:
            return "IP"
        return "NG"

    @classmethod
    def _status_label(cls, enrollment: Enrollment) -> str:
        status_value = cls._status_value(enrollment)
        if status_value == EnrollmentStatus.COMPLETED:
            return "Completed"
        if status_value == EnrollmentStatus.DROPPED:
            return "Dropped"
        if status_value == EnrollmentStatus.WITHDRAWN:
            return "Withdrawn"
        return "In Progress"

    @classmethod
    def _status_value(cls, enrollment: Enrollment) -> EnrollmentStatus:
        status_value = enrollment.status
        if isinstance(status_value, str):
            try:
                status_value = EnrollmentStatus(status_value)
            except ValueError:
                status_value = EnrollmentStatus.ENROLLED
        return status_value

    @classmethod
    def _load_enrollments(cls, db: Session, advisee_id: int):
        return (
            db.query(Enrollment, Section, Course, Term)
            .join(Section, Enrollment.sectionID == Section.sectionID)
            .join(Course, Enrollment.courseID == Course.courseID)
            .join(Term, Section.termID == Term.termID)
            .filter(Enrollment.adviseeID == advisee_id)
            .order_by(Term.startDate.desc(), Course.courseName.asc())
            .all()
        )

    @classmethod
    def _build_terms(cls, enrollments) -> List[TranscriptTerm]:
        terms: Dict[int, Dict] = {}

        for enrollment, section, course, term in enrollments:
            term_entry = terms.setdefault(
                term.termID,
                {
                    "term": term.code,
                    "courses": [],
                    "attempted": 0.0,
                    "earned": 0.0,
                },
            )

            status_value = cls._status_value(enrollment)
            grade = cls._normalize_grade(enrollment.grade, status_value)
            course_credits = float(course.credits or 0)
            status_label = cls._status_label(enrollment)

            term_entry["courses"].append(
                TranscriptCourse(
                    courseCode=course.courseName or f"Course {course.courseID}",
                    courseTitle=course.description or course.courseName or "Untitled course",
                    credits=course_credits,
                    grade=grade,
                    status=status_label,
                    term=term.code,
                )
            )

            if status_value not in {EnrollmentStatus.DROPPED, EnrollmentStatus.WITHDRAWN}:
                term_entry["attempted"] += course_credits
            if status_value == EnrollmentStatus.COMPLETED:
                term_entry["earned"] += float(enrollment.creditsEarned or course_credits or 0)

        transcript_terms: List[TranscriptTerm] = []
        for term_id, data in terms.items():
            term_courses = data["courses"]
            term_gpa = cls._calculate_gpa(term_courses)
            transcript_terms.append(
                TranscriptTerm(
                    term=data["term"],
                    termGpa=term_gpa,
                    creditsAttempted=data["attempted"],
                    creditsEarned=data["earned"],
                    courses=term_courses,
                )
            )

        transcript_terms.sort(key=lambda t: t.term, reverse=True)
        return transcript_terms

    @classmethod
    def _build_transcript(cls, db: Session, profile: AdviseeProfile, user: User) -> TranscriptResponse:
        enrollments = cls._load_enrollments(db, profile.adviseeID)
        terms = cls._build_terms(enrollments)

        cumulative_gpa = cls._calculate_gpa([course for term in terms for course in term.courses])
        total_credits = sum(term.creditsEarned for term in terms)

        classification = (
            profile.classification.value
            if hasattr(profile.classification, "value")
            else profile.classification
        )

        return TranscriptResponse(
            adviseeID=profile.adviseeID,
            studentName=user.username,
            username=user.username,
            major=profile.major,
            classification=classification,
            catalogYear=profile.degree_plan or "CAT2024",
            cumulativeGpa=cumulative_gpa,
            totalCredits=total_credits,
            terms=terms,
            updatedAt=profile.lastUpdated or datetime.utcnow(),
        )

    @classmethod
    def get_transcript_for_advisee(cls, db: Session, advisee_id: int, user_claims: Dict) -> TranscriptResponse:
        """
        Return transcript for a specific advisee.
        Students can only request their own record; advisors/admins can view all.
        """
        role = cls.normalize_role(user_claims.get("role"))

        if role == "student":
            cls._ensure_student_access(db, advisee_id, user_claims)
        elif role not in {"advisor", "admin"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view transcripts",
            )

        profile, user = cls._load_advisee(db, advisee_id)
        return cls._build_transcript(db, profile, user)

    @classmethod
    def get_transcript_for_user(cls, db: Session, user_claims: Dict) -> TranscriptResponse:
        """
        Convenience helper for /me-style requests.
        """
        username = (
            user_claims.get("uid")
            or user_claims.get("sub")
            or user_claims.get("cn")
            or ""
        )
        username = str(username).strip()
        profile = cls._resolve_advisee_for_user(db, username)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No advisee profile found for this account",
            )
        profile, user = cls._load_advisee(db, profile.adviseeID)
        return cls._build_transcript(db, profile, user)
