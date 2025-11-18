from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from db.database import get_db
from schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserRole
)
from services.user_service import UserService

router = APIRouter(
    prefix="/users",
    tags=["users"]
)


@router.get("/", response_model=List[UserResponse])
def get_users(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    username: Optional[str] = Query(None, description="Filter by username"),
    email: Optional[str] = Query(None, description="Filter by email"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    isActive: Optional[int] = Query(None, description="Filter by user activity: 0- inactive 1- active"),
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
    return UserService.get_all_users(
        db=db,
        userID=user_id,
        username=username,
        email=email,
        role=role,
        isActive=isActive,
        skip=skip,
        limit=limit
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific schedule by ID including all classes/sections.

    - **schedule_id**: The ID of the schedule to retrieve
    """
    return UserService.get_user_by_id(db=db, userID=user_id)


@router.post("/", response_model=UserResponse, status_code=201)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new schedule.

    - **adviseeID**: ID of the advisee/student
    - **termID**: ID of the academic term
    - **source**: Source of the schedule (USER, ADVISOR, SYSTEM) - defaults to USER
    - **status**: Status of the schedule (DRAFT, APPROVED, REJECTED) - defaults to DRAFT
    """
    return UserService.create_user(db=db, user_data=user)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing schedule.

    - **schedule_id**: The ID of the schedule to update
    - **status**: New status (DRAFT, APPROVED, REJECTED)
    - **source**: New source (USER, ADVISOR, SYSTEM)

    Note: Updating status to APPROVED/REJECTED will automatically set the corresponding timestamp.
    """
    return UserService.update_user(db=db, user_id=user_id, user_data=user)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a schedule.

    - **schedule_id**: The ID of the schedule to delete

    Note: This will cascade delete all classes associated with the schedule.
    """
    return UserService.delete_user(db=db, user_id=user_id)

