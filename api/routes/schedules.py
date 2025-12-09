from fastapi import APIRouter, Depends, Header, HTTPException, Query
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
    AIScheduleNotificationRequest,
)
from services.schedule_service import ScheduleService
from services.schedule_ai_service import ScheduleAISuggestionService
from services.openai_service import get_openai_service
from dependencies.auth import JWT_ALGO, JWT_SECRET, require_user
from schemas.user import UserRole
from jose import JWTError, jwt
from models.user import User

router = APIRouter(
    prefix="/schedules",
    tags=["schedules"]
)


def _normalize_role_label(value: Optional[str]) -> str:
    if not value or not isinstance(value, str):
        return ""
    normalized = value.strip().lower()
    if normalized in {"advisor", "adviser", "admin"}:
        return "advisor"
    if normalized in {"advisee", "student"}:
        return "student"
    return ""


def _decode_authorization_claims(authorization: Optional[str]) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        return {}
    token = authorization.split(" ", 1)[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except JWTError:
        return {}


def _resolve_actor_role_from_authorization(authorization: Optional[str]) -> str:
    claims = _decode_authorization_claims(authorization)
    for key in ("role", "roles"):
        value = claims.get(key)
        if isinstance(value, list):
            for entry in value:
                normalized = _normalize_role_label(entry)
                if normalized:
                    return normalized
        else:
            normalized = _normalize_role_label(value)
            if normalized:
                return normalized
    return "student"


def _resolve_actor_user_id(authorization: Optional[str], db: Session) -> Optional[int]:
    claims = _decode_authorization_claims(authorization)
    username = claims.get("uid") or claims.get("sub") or claims.get("cn")
    if not username:
        return None
    user = db.query(User).filter(User.username == username).first()
    return user.userID if user else None


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

    return ScheduleService.get_schedule_by_id(db=db, schedule_id=schedule_id)


@router.get("/{schedule_id}/sections", response_model=List[SectionSearchItem])
def search_sections_for_schedule(
    schedule_id: int,
    search: Optional[str] = Query(None, description="Search by course name, description, or CRN"),
    limit: Optional[int] = Query(None, ge=1, description="Optional max results"),
    db: Session = Depends(get_db)
):

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

    try:
        openai_service = get_openai_service()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    service = ScheduleAISuggestionService(db, openai_service)
    try:
        return await run_in_threadpool(service.generate, schedule_id, payload.note)
    except HTTPException:
        raise
    except Exception as exc: 
        raise HTTPException(
            status_code=502, detail=f"Failed to generate schedule suggestions: {exc}"
        ) from exc


@router.post("/{schedule_id}/suggestions/notify")
def notify_ai_schedule_application(
    schedule_id: int,
    payload: AIScheduleNotificationRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):

    ScheduleService.notify_ai_schedule_application(
        db=db,
        schedule_id=schedule_id,
        payload=payload,
        actor_user_id=_resolve_actor_user_id(authorization, db),
    )
    return {"message": "Notification queued."}


@router.post("/", response_model=ScheduleResponse, status_code=201)
def create_schedule(
    schedule: ScheduleCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):

    actor_role = _resolve_actor_role_from_authorization(authorization)
    actor_user_id = _resolve_actor_user_id(authorization, db)
    return ScheduleService.create_schedule(
        db=db,
        schedule_data=schedule,
        actor_role=actor_role,
        actor_user_id=actor_user_id,
    )


@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: int,
    schedule: ScheduleUpdate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):

    actor_user_id = _resolve_actor_user_id(authorization, db)
    return ScheduleService.update_schedule(
        db=db,
        schedule_id=schedule_id,
        schedule_data=schedule,
        actor_user_id=actor_user_id,
    )


@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_user),
):

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
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):

    actor_role = _resolve_actor_role_from_authorization(authorization)
    actor_user_id = _resolve_actor_user_id(authorization, db)
    return ScheduleService.add_class_to_schedule(
        db=db,
        schedule_id=schedule_id,
        section_id=class_data.sectionID,
        actor_role=actor_role,
        ai_assisted=class_data.aiAssisted,
        actor_user_id=actor_user_id,
    )


@router.delete("/{schedule_id}/classes/{class_id}", response_model=ScheduleResponse)
def remove_class_from_schedule(
    schedule_id: int,
    class_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):

    actor_role = _resolve_actor_role_from_authorization(authorization)
    actor_user_id = _resolve_actor_user_id(authorization, db)
    return ScheduleService.remove_class_from_schedule(
        db=db,
        schedule_id=schedule_id,
        class_id=class_id,
        actor_role=actor_role,
        actor_user_id=actor_user_id,
    )
