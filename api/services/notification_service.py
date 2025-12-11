from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from fastapi import HTTPException, status

from models.notification import Notification
from schemas.notification import (
    notificationCreate,
    notificationResponse
)
from models.advisee import AdviseeProfile
from models.user import User
from services.email_service import send_email, EmailData


class NotificationService:
    """Service layer for notification CRUD operations"""

    @staticmethod
    def _send_email_for_notification(db: Session, user_id: int, description: str):
        """Send an email to the user tied to this notification."""
        user = db.query(User).filter(User.userID == user_id).first()
        if not user or not user.email:
            return  # No email to send

        email_data = EmailData(
            subject="New Notification",
            recipient=user.email,
            body=description
        )

        send_email(email_data)


    @staticmethod
    def queue_notification(db: Session, user_id: Optional[int], description: str) -> Optional[Notification]:
        if not user_id:
            return None

        notification = Notification(
            userID=user_id,
            description=description,
            isRead=False,
            createdAt=datetime.utcnow()
        )
        db.add(notification)


        NotificationService._send_email_for_notification(db, user_id, description)

        return notification

    @staticmethod
    def notify_advisee_and_advisor(
        db: Session,
        advisee_id: int,
        description: str,
        include_advisee: bool = True,
        include_advisor: bool = True,
        actor_user_id: Optional[int] = None
    ) -> None:
        """
        Notify the advisee and/or their advisor.
        """
        mapping = (
            db.query(AdviseeProfile.userID, AdviseeProfile.advisorID)
            .filter(AdviseeProfile.adviseeID == advisee_id)
            .first()
        )
        if not mapping:
            return

        user_id, advisor_id = mapping
        recipients = []
        if include_advisee and user_id:
            recipients.append(user_id)
        if include_advisor and advisor_id:
            recipients.append(advisor_id)

        for recipient_id in set(recipients):
            if actor_user_id and actor_user_id == recipient_id:
                continue
            NotificationService.queue_notification(db, recipient_id, description)


    @staticmethod
    def get_all_notifications(
        db: Session,
        notification_id: Optional[int] = None,
        user_id: Optional[int] = None,
        is_read: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[notificationResponse]:
      
        query = db.query(Notification)

        if notification_id:
            query = query.filter(Notification.notificationID == notification_id)
        if user_id:
            query = query.filter(Notification.userID == user_id)
        if is_read is not None:
            query = query.filter(Notification.isRead == is_read)

        notifications = (
            query.order_by(Notification.createdAt.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        result = []
        for notification in notifications:
            result.append(notificationResponse(
                notificationID=notification.notificationID,
                userID=notification.userID,
                description=notification.description,
                isRead=notification.isRead,
                createdAt=notification.createdAt
            ))

        return result

    @staticmethod
    def get_notification_by_id(db: Session, notification_id: int) -> notificationResponse:
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
            isRead=notification.isRead,
            createdAt=notification.createdAt
        )

    @staticmethod
    def create_notification(db: Session, notification_data: notificationCreate) -> notificationResponse:

        new_notification = Notification(
            userID=notification_data.userID,
            description=notification_data.description,
            isRead=notification_data.isRead,
            createdAt=datetime.utcnow()
        )

        db.add(new_notification)
        db.commit()
        db.refresh(new_notification)

        NotificationService._send_email_for_notification(
            db,
            new_notification.userID,
            new_notification.description
        )

        return NotificationService.get_notification_by_id(db, new_notification.notificationID)


    @staticmethod
    def update_notification(db: Session, notification_id: int, is_read: bool) -> notificationResponse:
        notification = db.query(Notification).filter(Notification.notificationID == notification_id).first()

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notification with ID {notification_id} not found"
            )

        notification.isRead = is_read
        db.commit()
        db.refresh(notification)

        return notificationResponse(
            notificationID=notification.notificationID,
            userID=notification.userID,
            description=notification.description,
            isRead=notification.isRead,
            createdAt=notification.createdAt
        )

    @staticmethod
    def delete_notification(db: Session, notification_id: int) -> dict:
        notification = db.query(Notification).filter(Notification.notificationID == notification_id).first()

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notification with ID {notification_id} not found"
            )

        db.delete(notification)
        db.commit()

        return {"message": f"Notification {notification_id} deleted successfully"}
