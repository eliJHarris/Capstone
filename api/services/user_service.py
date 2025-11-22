from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from fastapi import HTTPException, status

from models.user import User
from schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserRole
)


class UserService:
    """Service layer for Schedule CRUD operations"""

    @staticmethod
    def get_all_users(
        db: Session,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
        role: Optional[UserRole] = None,
        isActive: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserResponse]:
        """
        Get all schedules with optional filtering
        """
        query = db.query(User)

        # Apply filters
        if user_id:
            query = query.filter(User.userID == user_id)
        if username:
            query = query.filter(User.username == username)
        if role:
            query = query.filter(User.role == role.value)
        if isActive:
            query = query.filter(User.isActive == isActive)

        users = query.offset(skip).limit(limit).all()

        # Build response with class count
        result = []
        for user in users:
            result.append(UserResponse(
                userID=user.userID,
                username=user.username,
                email=user.email,
                role=user.role,
                isActive=user.isActive,
                createdDate=user.createdDate
            ))

        return result

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> UserResponse:
        """
        Get a specific schedule by ID with all classes
        """
        user = db.query(User).filter(User.userID == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )



        return UserResponse(
            userID=user.userID,
                username=user.username,
                email=user.email,
                role=user.role,
                isActive=user.isActive,
                createdDate=user.createdDate
        )

    @staticmethod
    def create_user(db: Session, user_data: UserCreate) -> UserResponse:
        """
        Create a new schedule
        """

        # Create new schedule
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            role=user_data.role,
            isActive=user_data.isActive,
            createdDate=datetime.now()
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return UserService.get_user_by_id(db, new_user.userID)

    @staticmethod
    def update_user(db: Session, user_id: int, user_data: UserUpdate) -> UserResponse:
        """
        Update an existing schedule
        """
        user = db.query(User).filter(User.userID == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )

        user.username = user_data.username
        user.email = user_data.email
        user.isActive = user_data.isActive

        db.commit()
        db.refresh(user)

        return UserService.get_user_by_id(db, user_id)

    @staticmethod
    def delete_user(db: Session, user_id: int) -> dict:
        """
        Delete a schedule
        """
        user = db.query(User).filter(User.userID == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )

        db.delete(user)
        db.commit()

        return {"message": f"User {user_id} deleted successfully"}
