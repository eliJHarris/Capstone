from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from fastapi import HTTPException, status

from models.schedule import Schedule, Class, Section, Course, Term
from schemas.schedule import (
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
    ScheduleListResponse,
    ClassInSchedule,
    ScheduleStatus
)


class ScheduleService:
    """Service layer for Schedule CRUD operations"""

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
        query = db.query(Schedule).join(Term)

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
                source=schedule.source,
                status=schedule.status,
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
        schedule = db.query(Schedule).filter(Schedule.scheduleID == schedule_id).first()

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found"
            )

        # Get term info
        term = db.query(Term).filter(Term.termID == schedule.termID).first()

        # Get all classes with section and course info
        classes = db.query(Class).filter(Class.scheduleID == schedule_id).all()

        class_list = []
        for cls in classes:
            section = db.query(Section).filter(Section.sectionID == cls.sectionID).first()
            if section:
                course = db.query(Course).filter(Course.courseID == section.courseID).first()
                if course:
                    class_list.append(ClassInSchedule(
                        classID=cls.classID,
                        sectionID=cls.sectionID,
                        courseName=course.courseName,
                        courseDescription=course.description,
                        credits=course.credits,
                        crn=section.crn,
                        professorName=section.professorName,
                        createdDate=cls.createdDate
                    ))

        return ScheduleResponse(
            scheduleID=schedule.scheduleID,
            adviseeID=schedule.adviseeID,
            termID=schedule.termID,
            termCode=term.code if term else "",
            source=schedule.source,
            status=schedule.status,
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
            source=schedule_data.source,
            status=schedule_data.status,
            createdWhen=datetime.now(),
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
            schedule.status = schedule_data.status

            # Update timestamp based on status
            if schedule_data.status == ScheduleStatus.APPROVED:
                schedule.approvedWhen = datetime.now()
                schedule.rejectedWhen = None
            elif schedule_data.status == ScheduleStatus.REJECTED:
                schedule.rejectedWhen = datetime.now()
                schedule.approvedWhen = None
            elif schedule_data.status == ScheduleStatus.DRAFT:
                schedule.approvedWhen = None
                schedule.rejectedWhen = None

        if schedule_data.source is not None:
            schedule.source = schedule_data.source

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
            createdDate=datetime.now()
        )

        db.add(new_class)
        db.commit()

        return ScheduleService.get_schedule_by_id(db, schedule_id)

    @staticmethod
    def remove_class_from_schedule(db: Session, schedule_id: int, class_id: int) -> ScheduleResponse:
        """
        Remove a class from a schedule
        """
        # Verify class exists and belongs to the schedule
        cls = db.query(Class).filter(
            Class.classID == class_id,
            Class.scheduleID == schedule_id
        ).first()

        if not cls:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Class {class_id} not found in schedule {schedule_id}"
            )

        db.delete(cls)
        db.commit()

        return ScheduleService.get_schedule_by_id(db, schedule_id)
