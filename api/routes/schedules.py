from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from typing import List, Optional

from db.database import get_db
from schemas.schedule import (
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
    ScheduleListResponse,
    AddClassToSchedule,
    ScheduleStatus,
    SectionSearchItem,
    ScheduleSuggestionRequest,
    ScheduleSuggestionResponse,
)
from services.schedule_service import ScheduleService
from services.schedule_ai_service import ScheduleAISuggestionService
from services.openai_service import get_openai_service
from dependencies.auth import require_user
from schemas.user import UserRole

router = APIRouter(
    prefix="/schedules",
    tags=["schedules"]
)


@router.get("/", response_model=List[ScheduleListResponse])
def get_schedules(
    advisee_id: Optional[int] = Query(None, description="Filter by advisee ID"),
    advisee_name: Optional[str] = Query(None, description="Filter by advisee username"),
    term_id: Optional[int] = Query(None, description="Filter by term ID"),
    term_name: Optional[str] = Query(None, description="Filter by term code/name"),
    status: Optional[ScheduleStatus] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Get all schedules with optional filtering.

    - **advisee_id**: Filter by advisee ID
    - **advisee_name**: Filter by advisee username
    - **term_id**: Filter by term ID
    - **term_name**: Filter by term code/name
    - **status**: Filter by schedule status (DRAFT, APPROVED, REJECTED)
    - **skip**: Pagination - number of records to skip
    - **limit**: Pagination - maximum number of records to return
    """
    return ScheduleService.get_all_schedules(
        db=db,
        advisee_id=advisee_id,
        advisee_name=advisee_name,
        term_id=term_id,
        term_name=term_name,
        schedule_status=status,
        skip=skip,
        limit=limit
    )


@router.get("", response_model=List[ScheduleListResponse], include_in_schema=False)
def get_schedules_no_slash(
    advisee_id: Optional[int] = Query(None, description="Filter by advisee ID"),
    advisee_name: Optional[str] = Query(None, description="Filter by advisee username"),
    term_id: Optional[int] = Query(None, description="Filter by term ID"),
    term_name: Optional[str] = Query(None, description="Filter by term code/name"),
    status: Optional[ScheduleStatus] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Compatibility handler to avoid redirecting /schedules -> /schedules/ when callers omit the trailing slash.
    """
    return get_schedules(
        advisee_id=advisee_id,
        advisee_name=advisee_name,
        term_id=term_id,
        term_name=term_name,
        status=status,
        skip=skip,
        limit=limit,
        db=db,
    )

@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(
    schedule_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific schedule by ID including all classes/sections.

    - **schedule_id**: The ID of the schedule to retrieve
    """
    return ScheduleService.get_schedule_by_id(db=db, schedule_id=schedule_id)


@router.get("/{schedule_id}/sections", response_model=List[SectionSearchItem])
def search_sections_for_schedule(
    schedule_id: int,
    search: Optional[str] = Query(None, description="Search by course name, description, or CRN"),
    limit: Optional[int] = Query(None, ge=1, description="Optional max results"),
    db: Session = Depends(get_db)
):
    """
    List sections in the same term as the schedule, filtered by search, only OPEN sections.
    Passing no limit returns all matching sections.
    """
    return ScheduleService.list_sections_for_schedule(
        db=db,
        schedule_id=schedule_id,
        search=search,
        limit=limit,
    )


@router.post("/{schedule_id}/suggestions", response_model=ScheduleSuggestionResponse)
async def generate_schedule_suggestions(
    schedule_id: int,
    payload: ScheduleSuggestionRequest = ScheduleSuggestionRequest(),
    db: Session = Depends(get_db),
):
    """
    Generate AI-assisted schedule suggestions using current degree context and open sections.
    """
    try:
        openai_service = get_openai_service()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    service = ScheduleAISuggestionService(db, openai_service)
    try:
        return await run_in_threadpool(service.generate, schedule_id, payload.note)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502, detail=f"Failed to generate schedule suggestions: {exc}"
        ) from exc


@router.post("/", response_model=ScheduleResponse, status_code=201)
def create_schedule(
    schedule: ScheduleCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new schedule.

    - **adviseeID**: ID of the advisee/student
    - **termID**: ID of the academic term
    - **source**: Source of the schedule (USER, ADVISOR, SYSTEM) - defaults to USER
    - **status**: Status of the schedule (DRAFT, APPROVED, REJECTED) - defaults to DRAFT
    """
    return ScheduleService.create_schedule(db=db, schedule_data=schedule)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: int,
    schedule: ScheduleUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing schedule.

    - **schedule_id**: The ID of the schedule to update
    - **status**: New status (DRAFT, APPROVED, REJECTED)
    - **source**: New source (USER, ADVISOR, SYSTEM)

    Note: Updating status to APPROVED/REJECTED will automatically set the corresponding timestamp.
    """
    return ScheduleService.update_schedule(db=db, schedule_id=schedule_id, schedule_data=schedule)


@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_user),
):
    """
    Delete a schedule.

    - **schedule_id**: The ID of the schedule to delete

    Note: This will cascade delete all classes associated with the schedule.
    """
    role = str(current_user.get("role", "")).strip().lower()
    roles = current_user.get("roles") or []
    normalized_roles = {role}
    if isinstance(roles, list):
        normalized_roles.update(str(item).strip().lower() for item in roles if item)
    elif isinstance(roles, str):
        normalized_roles.add(roles.strip().lower())

    if {"advisee", UserRole.STUDENT.value.lower()} & normalized_roles:
        raise HTTPException(
            status_code=403,
            detail="Students are not allowed to delete schedules.",
        )
    return ScheduleService.delete_schedule(db=db, schedule_id=schedule_id)


@router.post("/{schedule_id}/classes", response_model=ScheduleResponse)
def add_class_to_schedule(
    schedule_id: int,
    class_data: AddClassToSchedule,
    db: Session = Depends(get_db)
):
    """
    Add a class (section) to a schedule.

    - **schedule_id**: The ID of the schedule
    - **sectionID**: The ID of the section to add

    Note: The section must belong to the same term as the schedule.
    """
    return ScheduleService.add_class_to_schedule(
        db=db,
        schedule_id=schedule_id,
        section_id=class_data.sectionID
    )


@router.delete("/{schedule_id}/classes/{class_id}", response_model=ScheduleResponse)
def remove_class_from_schedule(
    schedule_id: int,
    class_id: int,
    db: Session = Depends(get_db)
):
    """
    Remove a class from a schedule.

    - **schedule_id**: The ID of the schedule
    - **class_id**: The ID of the class to remove
    """
    return ScheduleService.remove_class_from_schedule(
        db=db,
        schedule_id=schedule_id,
        class_id=class_id
    )
