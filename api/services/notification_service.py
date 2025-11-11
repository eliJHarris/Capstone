from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from fastapi import HTTPException, status

from models.notification import Notification
from schemas.notification import (
    notificationCreate,
    notificationResponse
)


class NotificationService:
    """Service layer for Schedule CRUD operations"""

    @staticmethod
    def get_all_notifications(
        db: Session,
        notification_id: Optional[int] = None,
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[notificationResponse]:
        """
        Get all schedules with optional filtering
        """
        query = db.query(Notification)

        # Apply filters
        if notification_id:
            query = query.filter(Notification.notificationID == notification_id)
        if user_id:
            query = query.filter(Notification.userID == user_id)

        notifications = query.offset(skip).limit(limit).all()

        # Build response with class count
        result = []
        for notification in notifications:
            result.append(notificationResponse(
                notificationID=notification.notificationID,
                userID=notification.userID,
                description=notification.description,
                createdAt=notification.createdAt
            ))

        return result

    @staticmethod
    def get_notification_by_id(db: Session, notification_id: int) -> notificationResponse:
        """
        Get a specific schedule by ID with all classes
        """
        notification = db.query(Notification).filter(Notification.notificationID == notification_id).first()

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notification with ID {notification_id} not found"
            )

        return notificationResponse(
            notificationID=notification.notificationID,
            userID=notification.userID,
            description=notification.description,
            createdAt=notification.createdAt
        )

    @staticmethod
    def create_notification(db: Session, notification_data: notificationCreate) -> notificationResponse:
        """
        Create a new schedule
        """

        # Create new schedule
        new_notification = Notification(
            userID=notification_data.userID,
            description=notification_data.description,
            createdAt=datetime.now()
        )

        db.add(new_notification)
        db.commit()
        db.refresh(new_notification)

        return NotificationService.get_notification_by_id(db, new_notification.notificationID)

    @staticmethod
    def delete_notification(db: Session, notification_id: int) -> dict:
        """
        Delete a schedule
        """
        notification = db.query(Notification).filter(Notification.notificationID == notification_id).first()

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notification with ID {notification_id} not found"
            )

        db.delete(notification)
        db.commit()

        return {"message": f"Notification {notification_id} deleted successfully"}

