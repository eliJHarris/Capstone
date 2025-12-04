from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from db.database import get_db
from schemas.notification import (
    notificationCreate,
    notificationResponse,
    NotificationUpdate
)
from services.notification_service import NotificationService

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"]
)


@router.get("/", response_model=List[notificationResponse])
def get_notifications(
    notification_id: Optional[int] = Query(None, description="Filter by notification ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    is_read: Optional[bool] = Query(None, description="Filter by read/unread status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Get all schedules with optional filtering.

    - **advisee_id**: Filter by advisee ID
    - **term_id**: Filter by term ID
    - **status**: Filter by schedule status (DRAFT, APPROVED, REJECTED)
    - **skip**: Pagination - number of records to skip
    - **limit**: Pagination - maximum number of records to return
    """
    return NotificationService.get_all_notifications(
        db=db,
        notification_id=notification_id,
        user_id=user_id,
        is_read=is_read,
        skip=skip,
        limit=limit
    )


@router.get("/{notification_id}", response_model=notificationResponse)
def get_notification(
    notification_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific schedule by ID including all classes/sections.

    - **schedule_id**: The ID of the schedule to retrieve
    """
    return NotificationService.get_notification_by_id(db=db, notification_id=notification_id)


@router.post("/", response_model=notificationResponse, status_code=201)
def create_notification(
    notification: notificationCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new schedule.

    - **adviseeID**: ID of the advisee/student
    - **termID**: ID of the academic term
    - **source**: Source of the schedule (USER, ADVISOR, SYSTEM) - defaults to USER
    - **status**: Status of the schedule (DRAFT, APPROVED, REJECTED) - defaults to DRAFT
    """
    return NotificationService.create_notification(db=db, notification_data=notification)


@router.put("/{notification_id}", response_model=notificationResponse)
def update_notification(
    notification_id: int,
    payload: NotificationUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing notification's read status.

    - **notification_id**: The ID of the notification to update
    - **isRead**: New read/unread flag
    """
    return NotificationService.update_notification(db=db, notification_id=notification_id, is_read=payload.isRead)


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a schedule.

    - **schedule_id**: The ID of the schedule to delete

    Note: This will cascade delete all classes associated with the schedule.
    """
    return NotificationService.delete_notification(db=db, notification_id=notification_id)
