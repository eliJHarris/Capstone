from datetime import datetime
from enum import Enum
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os

app = FastAPI(title="Adviseme Core API")

# --- CORS (you can tighten origins in prod) ---
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "https://localhost,https://localhost:5173,https://localhost:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Secrets helper: prefer file if present ---
def _read_secret(path: str, fallback: str = "") -> str:
    try:
        if path and os.path.exists(path):
            with open(path, "r") as f:
                return f.read().strip()
    except Exception:
        pass
    return fallback

def _env_or_secret(var_name: str, default: str = "") -> str:
    file_path = os.getenv(f"{var_name}_FILE", "")
    if file_path:
        val = _read_secret(file_path, None)
        if val is not None:
            return val
    return os.getenv(var_name, default)

DB_HOST = os.getenv("DB_HOST", "adviseme-db")
DB_USER = os.getenv("DB_USER", "adviseme_app")
DB_NAME = os.getenv("DB_NAME", "adviseme")

DB_PASS = _read_secret(os.getenv("DB_PASS_FILE", ""), os.getenv("DB_PASS", "app_pass"))

JWT_SECRET = _env_or_secret("JWT_SECRET", "change-me")
JWT_ALGO = "HS256"

# URL-encode in case the password has special characters
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASS)}@{DB_HOST}/{DB_NAME}"

# Use pre_ping so dead connections get recycled
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)


class ScheduleStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ScheduleSource(str, Enum):
    USER = "USER"
    ADVISOR = "ADVISOR"
    SYSTEM = "SYSTEM"


class ScheduleCreate(BaseModel):
    adviseeID: int = Field(..., description="ID of the advisee")
    termID: int = Field(..., description="ID of the term")
    source: ScheduleSource = Field(default=ScheduleSource.USER)
    status: ScheduleStatus = Field(default=ScheduleStatus.DRAFT)


class ScheduleUpdate(BaseModel):
    status: Optional[ScheduleStatus] = None
    source: Optional[ScheduleSource] = None


class AddClassRequest(BaseModel):
    sectionID: int


class ClassInSchedule(BaseModel):
    classID: int
    sectionID: int
    courseName: str
    courseDescription: Optional[str]
    credits: int
    crn: str
    professorName: Optional[str]
    createdDate: datetime

    class Config:
        orm_mode = True


class ScheduleResponse(BaseModel):
    scheduleID: int
    adviseeID: int
    termID: int
    termCode: str
    source: ScheduleSource
    status: ScheduleStatus
    createdWhen: datetime
    approvedWhen: Optional[datetime]
    rejectedWhen: Optional[datetime]
    classes: List[ClassInSchedule] = Field(default_factory=list)

    class Config:
        orm_mode = True


class ScheduleListResponse(BaseModel):
    scheduleID: int
    adviseeID: int
    termID: int
    termCode: str
    source: ScheduleSource
    status: ScheduleStatus
    createdWhen: datetime
    approvedWhen: Optional[datetime]
    rejectedWhen: Optional[datetime]
    classCount: int

    class Config:
        orm_mode = True

def verify_token(authorization: str = Header(...)):
    """Verify Bearer JWT token and return claims."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

@app.get("/")
def root():
    return {"message": "Core API online"}

@app.get("/health")
def health():
    # lightweight DB ping
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "degraded", "error": str(e)}

@app.get("/me")
def me(user=Depends(verify_token)):
    """Return JWT claims so the UI can show who is logged in."""
    return {"user": user}

@app.get("/db")
def test_db(user=Depends(verify_token)):
    """Confirm DB connection and return version."""
    with engine.connect() as conn:
        ver = conn.execute(text("SELECT VERSION()")).scalar_one()
    return {"authenticated_user": user.get("sub"), "db_version": ver}


SCHEDULE_DETAIL_SQL = """
SELECT s.scheduleID,
       s.adviseeID,
       s.termID,
       t.code AS termCode,
       s.source,
       s.status,
       s.createdWhen,
       s.approvedWhen,
       s.rejectedWhen
FROM schedules s
JOIN terms t ON t.termID = s.termID
WHERE s.scheduleID = :schedule_id
"""

CLASS_LIST_SQL = """
SELECT c.classID,
       c.sectionID,
       c.createdDate,
       sec.crn,
       sec.professorName,
       co.courseName,
       co.description AS courseDescription,
       co.credits
FROM classes c
JOIN sections sec ON sec.sectionID = c.sectionID
JOIN courses co ON co.courseID = sec.courseID
WHERE c.scheduleID = :schedule_id
ORDER BY c.createdDate ASC
"""


def _schedule_with_classes(schedule_id: int) -> dict:
    with engine.connect() as conn:
        schedule = conn.execute(text(SCHEDULE_DETAIL_SQL), {"schedule_id": schedule_id}).mappings().first()
        if not schedule:
            raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
        classes = conn.execute(text(CLASS_LIST_SQL), {"schedule_id": schedule_id}).mappings().all()
        schedule = dict(schedule)
        schedule["classes"] = [dict(row) for row in classes]
        return schedule


def _ensure_term_exists(conn, term_id: int):
    term = conn.execute(text("SELECT termID FROM terms WHERE termID = :term_id"), {"term_id": term_id}).first()
    if not term:
        raise HTTPException(status_code=404, detail=f"Term {term_id} not found")


@app.get("/schedules", response_model=List[ScheduleListResponse])
def list_schedules(
    advisee_id: Optional[int] = None,
    term_id: Optional[int] = None,
    status: Optional[ScheduleStatus] = None,
    skip: int = 0,
    limit: int = 100,
    user=Depends(verify_token),
):
    params = {"offset": skip, "limit": limit}
    filters = []

    if advisee_id is not None:
        filters.append("s.adviseeID = :advisee_id")
        params["advisee_id"] = advisee_id
    if term_id is not None:
        filters.append("s.termID = :term_id")
        params["term_id"] = term_id
    if status is not None:
        filters.append("s.status = :status")
        params["status"] = status.value

    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = " AND " + where_clause

    query = f"""
    SELECT s.scheduleID,
           s.adviseeID,
           s.termID,
           t.code AS termCode,
           s.source,
           s.status,
           s.createdWhen,
           s.approvedWhen,
           s.rejectedWhen,
           (SELECT COUNT(*) FROM classes c WHERE c.scheduleID = s.scheduleID) AS classCount
    FROM schedules s
    JOIN terms t ON t.termID = s.termID
    WHERE 1=1 {where_clause}
    ORDER BY s.createdWhen DESC
    LIMIT :limit OFFSET :offset
    """

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().all()
        return [dict(row) for row in rows]


@app.get("/schedules/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(schedule_id: int, user=Depends(verify_token)):
    return _schedule_with_classes(schedule_id)


@app.post("/schedules", response_model=ScheduleResponse, status_code=201)
def create_schedule(payload: ScheduleCreate, user=Depends(verify_token)):
    now = datetime.utcnow()
    with engine.begin() as conn:
        _ensure_term_exists(conn, payload.termID)
        result = conn.execute(
            text(
                """
            INSERT INTO schedules (adviseeID, termID, source, status, createdWhen, approvedWhen, rejectedWhen)
            VALUES (:adviseeID, :termID, :source, :status, :createdWhen, NULL, NULL)
            """
            ),
            {
                "adviseeID": payload.adviseeID,
                "termID": payload.termID,
                "source": payload.source.value,
                "status": payload.status.value,
                "createdWhen": now,
            },
        )
        schedule_id = result.lastrowid
    return _schedule_with_classes(schedule_id)


@app.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(schedule_id: int, payload: ScheduleUpdate, user=Depends(verify_token)):
    updates = []
    params = {"schedule_id": schedule_id}

    if payload.status is not None:
        updates.append("status = :status")
        params["status"] = payload.status.value
        now = datetime.utcnow()
        if payload.status == ScheduleStatus.APPROVED:
            params["approvedWhen"] = now
            params["rejectedWhen"] = None
        elif payload.status == ScheduleStatus.REJECTED:
            params["approvedWhen"] = None
            params["rejectedWhen"] = now
        else:
            params["approvedWhen"] = None
            params["rejectedWhen"] = None
        updates.append("approvedWhen = :approvedWhen")
        updates.append("rejectedWhen = :rejectedWhen")

    if payload.source is not None:
        updates.append("source = :source")
        params["source"] = payload.source.value

    if not updates:
        return _schedule_with_classes(schedule_id)

    set_clause = ", ".join(updates)

    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM schedules WHERE scheduleID = :schedule_id"),
            {"schedule_id": schedule_id},
        ).first()
        if not exists:
            raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
        conn.execute(text(f"UPDATE schedules SET {set_clause} WHERE scheduleID = :schedule_id"), params)

    return _schedule_with_classes(schedule_id)


@app.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: int, user=Depends(verify_token)):
    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM schedules WHERE scheduleID = :schedule_id"),
            {"schedule_id": schedule_id},
        ).first()
        if not exists:
            raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
        conn.execute(text("DELETE FROM classes WHERE scheduleID = :schedule_id"), {"schedule_id": schedule_id})
        conn.execute(text("DELETE FROM schedules WHERE scheduleID = :schedule_id"), {"schedule_id": schedule_id})
    return {"message": f"Schedule {schedule_id} deleted successfully"}


@app.post("/schedules/{schedule_id}/classes", response_model=ScheduleResponse)
def add_class_to_schedule(schedule_id: int, payload: AddClassRequest, user=Depends(verify_token)):
    with engine.begin() as conn:
        schedule = conn.execute(
            text("SELECT scheduleID, termID FROM schedules WHERE scheduleID = :schedule_id"),
            {"schedule_id": schedule_id},
        ).mappings().first()
        if not schedule:
            raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

        section = conn.execute(
            text("SELECT sectionID, termID FROM sections WHERE sectionID = :section_id"),
            {"section_id": payload.sectionID},
        ).mappings().first()
        if not section:
            raise HTTPException(status_code=404, detail=f"Section {payload.sectionID} not found")

        if section["termID"] != schedule["termID"]:
            raise HTTPException(
                status_code=400,
                detail=f"Section term {section['termID']} does not match schedule term {schedule['termID']}",
            )

        exists = conn.execute(
            text(
                """
            SELECT 1 FROM classes
            WHERE scheduleID = :schedule_id AND sectionID = :section_id
            """
            ),
            {"schedule_id": schedule_id, "section_id": payload.sectionID},
        ).first()
        if exists:
            raise HTTPException(
                status_code=400,
                detail=f"Section {payload.sectionID} already exists in schedule {schedule_id}",
            )

        conn.execute(
            text(
                """
            INSERT INTO classes (sectionID, scheduleID, createdDate)
            VALUES (:section_id, :schedule_id, :created_date)
            """
            ),
            {
                "section_id": payload.sectionID,
                "schedule_id": schedule_id,
                "created_date": datetime.utcnow(),
            },
        )

    return _schedule_with_classes(schedule_id)


@app.delete("/schedules/{schedule_id}/classes/{class_id}", response_model=ScheduleResponse)
def remove_class_from_schedule(schedule_id: int, class_id: int, user=Depends(verify_token)):
    with engine.begin() as conn:
        cls = conn.execute(
            text(
                """
            SELECT classID FROM classes
            WHERE classID = :class_id AND scheduleID = :schedule_id
            """
            ),
            {"class_id": class_id, "schedule_id": schedule_id},
        ).first()
        if not cls:
            raise HTTPException(
                status_code=404, detail=f"Class {class_id} not found in schedule {schedule_id}"
            )
        conn.execute(
            text("DELETE FROM classes WHERE classID = :class_id AND scheduleID = :schedule_id"),
            {"class_id": class_id, "schedule_id": schedule_id},
        )

    return _schedule_with_classes(schedule_id)
