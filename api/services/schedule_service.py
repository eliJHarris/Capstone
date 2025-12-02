from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from fastapi import HTTPException, status

from models.schedule import (
    Schedule,
    Class,
    Section,
    Course,
    Term,
    ScheduleStatusEnum,
    ScheduleSourceEnum,
    SectionStatusEnum,
)
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
    def list_sections_for_schedule(
        db: Session,
        schedule_id: int,
        search: Optional[str] = None,
        limit: int = 20,
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

        query = query.order_by(Course.courseName.asc(), Section.crn.asc()).limit(limit)
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
        term_id: Optional[int] = None,
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
            .options(joinedload(Schedule.term))
            .order_by(Schedule.createdWhen.desc())
        )

        # Apply filters
        if advisee_id:
            query = query.filter(Schedule.adviseeID == advisee_id)
        if term_id:
            query = query.filter(Schedule.termID == term_id)
        if schedule_status:
            query = query.filter(Schedule.status == schedule_status.value)

        schedules = query.offset(skip).limit(limit).all()

        # Build response with class count
        result = []
        for schedule in schedules:
            class_count = db.query(Class).filter(Class.scheduleID == schedule.scheduleID).count()
            term = db.query(Term).filter(Term.termID == schedule.termID).first()

            result.append(ScheduleListResponse(
                scheduleID=schedule.scheduleID,
                adviseeID=schedule.adviseeID,
                termID=schedule.termID,
                termCode=term.code if term else "",
                source=ScheduleService._status_value(schedule.source),
                status=ScheduleService._status_value(schedule.status),
                createdWhen=schedule.createdWhen,
                approvedWhen=schedule.approvedWhen,
                rejectedWhen=schedule.rejectedWhen,
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
            termID=schedule.termID,
            termCode=schedule.term.code if schedule.term else "",
            source=ScheduleService._status_value(schedule.source),
            status=ScheduleService._status_value(schedule.status),
            createdWhen=schedule.createdWhen,
            approvedWhen=schedule.approvedWhen,
            rejectedWhen=schedule.rejectedWhen,
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
            rejectedWhen=None
        )

        db.add(new_schedule)
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

            schedule.status = ScheduleStatusEnum(schedule_data.status.value)

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

        # Create new class
        new_class = Class(
            sectionID=section_id,
            scheduleID=schedule_id,
            createdDate=datetime.utcnow()
        )

        db.add(new_class)
        section.enrolled = min(section.capacity, section.enrolled + 1)
        db.commit()

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

        db.delete(cls)
        db.commit()

        return ScheduleService.get_schedule_by_id(db, schedule_id)
