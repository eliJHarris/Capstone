from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime
from fastapi import HTTPException, status

from models.schedule import (
    Schedule,
    Class,
    Section,
    Course,
    CoursePrerequisite,
    Term,
    ScheduleStatusEnum,
    ScheduleSourceEnum,
    SectionStatusEnum,
)
from models.enrollment import Enrollment, EnrollmentStatus
from models.advisee import AdviseeProfile
from models.user import User
from services.notification_service import NotificationService
from schemas.schedule import (
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
    ScheduleListResponse,
    ClassInSchedule,
    ScheduleStatus,
    SectionSearchItem,
)


class ScheduleService:
    """Service layer for Schedule CRUD operations"""

    @staticmethod
    def _status_value(value) -> str:
        return value.value if hasattr(value, "value") else str(value)

    @staticmethod
    def _term_code(db: Session, term_id: int) -> str:
        term_code = db.query(Term.code).filter(Term.termID == term_id).scalar()
        return term_code or str(term_id)

    @staticmethod
    def _validate_prerequisites(db: Session, advisee_id: int, target_course_id: int) -> None:
        """
        Ensure an advisee has completed the prerequisites for a course.
        Mirrors the database trigger logic by requiring completed enrollments with earned credit.
        """
        prereqs = (
            db.query(CoursePrerequisite.prerequisiteCourseID, Course.courseName)
            .join(Course, Course.courseID == CoursePrerequisite.prerequisiteCourseID)
            .filter(CoursePrerequisite.courseID == target_course_id)
            .all()
        )
        if not prereqs:
            return

        completed_course_ids = {
            course_id
            for (course_id,) in (
                db.query(Enrollment.courseID)
                .filter(
                    Enrollment.adviseeID == advisee_id,
                    Enrollment.status == EnrollmentStatus.COMPLETED,
                    Enrollment.creditsEarned > 0,
                )
                .all()
            )
        }

        missing = [
            name or f"Course {prereq_id}"
            for prereq_id, name in prereqs
            if prereq_id not in completed_course_ids
        ]

        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing prerequisites: " + ", ".join(missing),
            )

    @staticmethod
    def list_sections_for_schedule(
        db: Session,
        schedule_id: int,
        search: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[SectionSearchItem]:
        schedule = db.query(Schedule).filter(Schedule.scheduleID == schedule_id).first()
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found",
            )

        query = (
            db.query(Section)
            .join(Course)
            .filter(
                Section.termID == schedule.termID,
                Section.status == SectionStatusEnum.OPEN,
            )
        )

        if search:
            like = f"%{search}%"
            query = query.filter(
                (Course.courseName.ilike(like))
                | (Course.description.ilike(like))
                | (Section.crn.ilike(like))
            )

        query = query.order_by(Course.courseName.asc(), Section.crn.asc())

        if limit:
            query = query.limit(limit)
        sections = query.all()

        results: List[SectionSearchItem] = []
        for section in sections:
            course = section.course
            results.append(
                SectionSearchItem(
                    sectionID=section.sectionID,
                    crn=section.crn,
                    courseName=course.courseName,
                    courseDescription=course.description,
                    professorName=section.professorName,
                    credits=course.credits,
                    capacity=section.capacity,
                    enrolled=section.enrolled,
                    seatsRemaining=max(section.capacity - section.enrolled, 0),
                    status=ScheduleService._status_value(section.status),
                )
            )
        return results

    @staticmethod
    def get_all_schedules(
        db: Session,
        advisee_id: Optional[int] = None,
        advisee_name: Optional[str] = None,
        term_id: Optional[int] = None,
        term_name: Optional[str] = None,
        schedule_status: Optional[ScheduleStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ScheduleListResponse]:
        """
        Get all schedules with optional filtering
        """
        query = (
            db.query(Schedule)
            .join(Term)
            .join(AdviseeProfile, AdviseeProfile.adviseeID == Schedule.adviseeID)
            .join(User, User.userID == AdviseeProfile.userID)
            .options(joinedload(Schedule.term))
            .order_by(Schedule.createdWhen.desc())
        )

        # Apply filters
        if advisee_id:
            query = query.filter(Schedule.adviseeID == advisee_id)
        if advisee_name:
            query = query.filter(User.username.ilike(f"%{advisee_name}%"))
        if term_id:
            query = query.filter(Schedule.termID == term_id)
        if term_name:
            query = query.filter(Term.code.ilike(f"%{term_name}%"))
        if schedule_status:
            query = query.filter(Schedule.status == schedule_status.value)

        schedules = query.offset(skip).limit(limit).all()

        advisee_ids = [schedule.adviseeID for schedule in schedules]
        advisee_name_map = {}
        if advisee_ids:
            rows = (
                db.query(AdviseeProfile.adviseeID, User.username)
                .join(User, User.userID == AdviseeProfile.userID)
                .filter(AdviseeProfile.adviseeID.in_(advisee_ids))
                .all()
            )
            advisee_name_map = {advisee_id: username for advisee_id, username in rows}

        # Build response with class count
        result = []
        for schedule in schedules:
            class_count = db.query(Class).filter(Class.scheduleID == schedule.scheduleID).count()
            result.append(ScheduleListResponse(
                scheduleID=schedule.scheduleID,
                adviseeID=schedule.adviseeID,
                adviseeName=advisee_name_map.get(schedule.adviseeID, ""),
                termID=schedule.termID,
                termCode=schedule.term.code if schedule.term else "",
                termName=schedule.term.code if schedule.term else "",
                source=ScheduleService._status_value(schedule.source),
                status=ScheduleService._status_value(schedule.status),
                createdWhen=schedule.createdWhen,
                approvedWhen=schedule.approvedWhen,
                rejectedWhen=schedule.rejectedWhen,
                advisorFeedback=schedule.advisorFeedback,
                classCount=class_count
            ))

        return result

    @staticmethod
    def get_schedule_by_id(db: Session, schedule_id: int) -> ScheduleResponse:
        """
        Get a specific schedule by ID with all classes
        """
        schedule = (
            db.query(Schedule)
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
                detail=f"Schedule with ID {schedule_id} not found"
            )

        class_list = []
        for cls in schedule.classes:
            section = cls.section
            course = section.course if section else None
            if section and course:
                class_list.append(
                    ClassInSchedule(
                        classID=cls.classID,
                        sectionID=cls.sectionID,
                        sectionStatus=ScheduleService._status_value(section.status),
                        capacity=section.capacity,
                        enrolled=section.enrolled,
                        seatsRemaining=max(section.capacity - section.enrolled, 0),
                        courseName=course.courseName,
                        courseDescription=course.description,
                        credits=course.credits,
                        crn=section.crn,
                        professorName=section.professorName,
                        createdDate=cls.createdDate,
                )
                )

        return ScheduleResponse(
            scheduleID=schedule.scheduleID,
            adviseeID=schedule.adviseeID,
            adviseeName=(
                db.query(User.username)
                .join(AdviseeProfile, AdviseeProfile.userID == User.userID)
                .filter(AdviseeProfile.adviseeID == schedule.adviseeID)
                .scalar()
                or ""
            ),
            termID=schedule.termID,
            termCode=schedule.term.code if schedule.term else "",
            termName=schedule.term.code if schedule.term else "",
            source=ScheduleService._status_value(schedule.source),
            status=ScheduleService._status_value(schedule.status),
            createdWhen=schedule.createdWhen,
            approvedWhen=schedule.approvedWhen,
            rejectedWhen=schedule.rejectedWhen,
            advisorFeedback=schedule.advisorFeedback,
            classes=class_list
        )

    @staticmethod
    def create_schedule(db: Session, schedule_data: ScheduleCreate) -> ScheduleResponse:
        """
        Create a new schedule
        """
        # Verify term exists
        term = db.query(Term).filter(Term.termID == schedule_data.termID).first()
        if not term:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Term with ID {schedule_data.termID} not found"
            )

        # Create new schedule
        new_schedule = Schedule(
            adviseeID=schedule_data.adviseeID,
            termID=schedule_data.termID,
            source=ScheduleSourceEnum(schedule_data.source.value),
            status=ScheduleStatusEnum(schedule_data.status.value),
            createdWhen=datetime.utcnow(),
            approvedWhen=None,
            rejectedWhen=None,
            advisorFeedback=schedule_data.advisorFeedback,
        )

        db.add(new_schedule)
        db.flush()

        NotificationService.notify_advisee_and_advisor(
            db,
            advisee_id=schedule_data.adviseeID,
            description=(
                f"Schedule {new_schedule.scheduleID} created for term "
                f"{term.code} with status {new_schedule.status.value}."
            ),
        )
        db.commit()
        db.refresh(new_schedule)

        return ScheduleService.get_schedule_by_id(db, new_schedule.scheduleID)

    @staticmethod
    def update_schedule(db: Session, schedule_id: int, schedule_data: ScheduleUpdate) -> ScheduleResponse:
        """
        Update an existing schedule
        """
        schedule = db.query(Schedule).filter(Schedule.scheduleID == schedule_id).first()

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found"
        )

        status_changed = False
        # Update fields if provided
        if schedule_data.status is not None:
            if (
                schedule_data.status == ScheduleStatus.APPROVED
                and db.query(Class).filter(Class.scheduleID == schedule_id).count() == 0
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot approve a schedule with no classes",
                )

            new_status = ScheduleStatusEnum(schedule_data.status.value)
            if schedule.status != new_status:
                status_changed = True
            schedule.status = new_status

            # Update timestamp based on status
            if schedule_data.status == ScheduleStatus.APPROVED:
                schedule.approvedWhen = datetime.utcnow()
                schedule.rejectedWhen = None
            elif schedule_data.status == ScheduleStatus.REJECTED:
                schedule.rejectedWhen = datetime.utcnow()
                schedule.approvedWhen = None
            elif schedule_data.status == ScheduleStatus.DRAFT:
                schedule.approvedWhen = None
                schedule.rejectedWhen = None

        if schedule_data.source is not None:
            schedule.source = ScheduleSourceEnum(schedule_data.source.value)
        if schedule_data.advisorFeedback is not None:
            schedule.advisorFeedback = schedule_data.advisorFeedback.strip() or None

        if status_changed:
            term_code = ScheduleService._term_code(db, schedule.termID)
            NotificationService.notify_advisee_and_advisor(
                db,
                advisee_id=schedule.adviseeID,
                description=(
                    f"Schedule {schedule_id} status updated to "
                    f"{schedule.status.value} for term {term_code}."
                ),
            )

        db.commit()
        db.refresh(schedule)

        return ScheduleService.get_schedule_by_id(db, schedule_id)

    @staticmethod
    def delete_schedule(db: Session, schedule_id: int) -> dict:
        """
        Delete a schedule
        """
        schedule = db.query(Schedule).filter(Schedule.scheduleID == schedule_id).first()

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found"
            )

        db.delete(schedule)
        db.commit()

        return {"message": f"Schedule {schedule_id} deleted successfully"}

    @staticmethod
    def add_class_to_schedule(db: Session, schedule_id: int, section_id: int) -> ScheduleResponse:
        """
        Add a class (section) to a schedule
        """
        # Verify schedule exists
        schedule = db.query(Schedule).filter(Schedule.scheduleID == schedule_id).first()
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found"
        )

        if ScheduleService._status_value(schedule.status) != ScheduleStatus.DRAFT.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only DRAFT schedules can be modified",
            )

        # Verify section exists
        section = db.query(Section).filter(Section.sectionID == section_id).first()
        if not section:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Section with ID {section_id} not found"
            )

        # Check if section belongs to the same term as schedule
        if section.termID != schedule.termID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Section belongs to term {section.termID} but schedule is for term {schedule.termID}"
        )

        if ScheduleService._status_value(section.status) != SectionStatusEnum.OPEN.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Section {section_id} is not open for scheduling",
            )

        if section.enrolled >= section.capacity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Section {section_id} is full",
            )

        # Check if class already exists in schedule
        existing_class = db.query(Class).filter(
            Class.scheduleID == schedule_id,
            Class.sectionID == section_id
        ).first()

        if existing_class:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Section {section_id} is already in schedule {schedule_id}"
            )

        # Validate that the advisee has completed required prerequisites before scheduling
        ScheduleService._validate_prerequisites(
            db=db,
            advisee_id=schedule.adviseeID,
            target_course_id=section.courseID,
        )

        # Create new class
        new_class = Class(
            sectionID=section_id,
            scheduleID=schedule_id,
            termID=schedule.termID,
            createdDate=datetime.utcnow()
        )

        db.add(new_class)
        section.enrolled = min(section.capacity, section.enrolled + 1)

        # Mirror the scheduled class into enrollments so the transcript view reflects in-progress courses
        existing_enrollment = (
            db.query(Enrollment)
            .filter(
                Enrollment.adviseeID == schedule.adviseeID,
                Enrollment.sectionID == section_id,
            )
            .first()
        )
        if not existing_enrollment:
            db.add(
                Enrollment(
                    adviseeID=schedule.adviseeID,
                    sectionID=section_id,
                    courseID=section.courseID,
                    status=EnrollmentStatus.ENROLLED,
                    grade=None,
                    creditsEarned=0,
                    attemptedNumber=1,
                    createdWhen=datetime.utcnow(),
                )
            )

        course_name = section.course.courseName if section.course else "Section"
        term_code = ScheduleService._term_code(db, schedule.termID)
        NotificationService.notify_advisee_and_advisor(
            db,
            advisee_id=schedule.adviseeID,
            description=(
                f"Added {course_name} ({section.crn}) to schedule "
                f"{schedule_id} for term {term_code}."
            ),
        )

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # Surface a clear message instead of a 500 when constraints are hit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to add class due to a database constraint (likely duplicate section for this schedule)",
            )

        return ScheduleService.get_schedule_by_id(db, schedule_id)

    @staticmethod
    def remove_class_from_schedule(db: Session, schedule_id: int, class_id: int) -> ScheduleResponse:
        """
        Remove a class from a schedule
        """
        cls = (
            db.query(Class)
            .options(joinedload(Class.section), joinedload(Class.schedule))
            .filter(Class.classID == class_id, Class.scheduleID == schedule_id)
            .first()
        )

        if not cls:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Class {class_id} not found in schedule {schedule_id}"
            )

        if ScheduleService._status_value(cls.schedule.status) != ScheduleStatus.DRAFT.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only DRAFT schedules can be modified",
        )

        # Keep capacity accounting accurate
        if cls.section and cls.section.enrolled > 0:
            cls.section.enrolled -= 1

        # Remove the mirrored enrollment so the transcript no longer lists the course
        enrollment = (
            db.query(Enrollment)
            .filter(
                Enrollment.adviseeID == cls.schedule.adviseeID,
                Enrollment.sectionID == cls.sectionID,
                Enrollment.status == EnrollmentStatus.ENROLLED,
            )
            .first()
        )
        if enrollment:
            db.delete(enrollment)

        course_name = cls.section.course.courseName if cls.section and cls.section.course else "Section"
        crn = cls.section.crn if cls.section else "class"
        term_code = ScheduleService._term_code(db, cls.schedule.termID)
        NotificationService.notify_advisee_and_advisor(
            db,
            advisee_id=cls.schedule.adviseeID,
            description=(
                f"Removed {course_name} ({crn}) from schedule "
                f"{schedule_id} for term {term_code}."
            ),
        )

        db.delete(cls)
        db.commit()

        return ScheduleService.get_schedule_by_id(db, schedule_id)
