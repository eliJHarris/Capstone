from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from db.database import get_db
from schemas.notification import (
    notificationCreate,
    notificationResponse,
    NotificationUpdate
)

from services.email_service import send_email, EmailData
from fastapi import BackgroundTasks

from services.notification_service import NotificationService
from dependencies.auth import require_user
from models.user import User
from routes.users import get_user
from routes.emails import notify_user
router = APIRouter(
    prefix="/notifications",
    tags=["notifications"]
)


def _resolve_current_user_id(db: Session, claims: dict) -> Optional[int]:
    """
    Map JWT claims to a userID in the database (using username-like fields).
    """
    username = claims.get("uid") or claims.get("sub") or claims.get("cn")
    if not username:
        return None
    user = db.query(User).filter(User.username == username).first()
    return user.userID if user else None


def _list_notifications(
    notification_id: Optional[int],
    user_id: Optional[int],
    is_read: Optional[bool],
    skip: int,
    limit: int,
    db: Session,
):
    return NotificationService.get_all_notifications(
        db=db,
        notification_id=notification_id,
        user_id=user_id,
        is_read=is_read,
        skip=skip,
        limit=limit
    )


@router.get("/", response_model=List[notificationResponse])
def get_notifications(
    notification_id: Optional[int] = Query(None, description="Filter by notification ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    is_read: Optional[bool] = Query(None, description="Filter by read/unread status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    claims: dict = Depends(require_user),
):
    """
    Get all notifications with optional filtering.
    """
    current_user_id = _resolve_current_user_id(db, claims)
    effective_user_id = user_id or current_user_id

    if current_user_id and user_id and user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to view another user's notifications.",
        )

    if not effective_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not resolve user for notifications.",
        )

    return _list_notifications(notification_id, effective_user_id, is_read, skip, limit, db)


@router.get("", response_model=List[notificationResponse], include_in_schema=False)
def get_notifications_no_trailing_slash(
    notification_id: Optional[int] = Query(None, description="Filter by notification ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    is_read: Optional[bool] = Query(None, description="Filter by read/unread status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    claims: dict = Depends(require_user),
):
    """Alias to serve /notifications without a trailing slash (avoids 307 redirects)."""
    return get_notifications(
        notification_id=notification_id,
        user_id=user_id,
        is_read=is_read,
        skip=skip,
        limit=limit,
        db=db,
        claims=claims,
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
    background: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = get_user(notification.userID, db)
    email_data = EmailData(
        subject="New Notification",
        recipient=user.email,
        body=f"Hi {user.username}, you have a new notification."
    )

    background.add_task(send_email, email_data)

    return NotificationService.create_notification(db=db, notification_data=notification)


@router.put("/{notification_id}", response_model=notificationResponse)
def update_notification(
    notification_id: int,
    payload: NotificationUpdate,
    db: Session = Depends(get_db)
):

    return NotificationService.update_notification(db=db, notification_id=notification_id, is_read=payload.isRead)


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db)
):

    return NotificationService.delete_notification(db=db, notification_id=notification_id)
