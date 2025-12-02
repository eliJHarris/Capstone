from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional
import os
import sys
import time
import json
import re

from pdf_scraper.scrape_pdfs import run_pdf_scraper
from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# Import patched scraper
from pdf_scraper.scrape_pdfs import run_pdf_scraper

app = FastAPI(title="Adviseme Core API")

# --- CORS ---
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

# --- Secrets helper ---
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

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASS)}@{DB_HOST}/{DB_NAME}"
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

API_WORKDIR = Path(os.getenv("API_WORKDIR", "/code")).resolve()

# ---------- Models ----------
class ScheduleStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class ScheduleSource(str, Enum):
    USER = "USER"
    ADVISOR = "ADVISOR"
    SYSTEM = "SYSTEM"

class SectionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

class ScheduleCreate(BaseModel):
    adviseeID: int
    termID: int
    source: ScheduleSource = ScheduleSource.USER
    status: ScheduleStatus = ScheduleStatus.DRAFT

class ScheduleUpdate(BaseModel):
    status: Optional[ScheduleStatus] = None
    source: Optional[ScheduleSource] = None

class AddClassRequest(BaseModel):
    sectionID: int

class ClassInSchedule(BaseModel):
    classID: int
    sectionID: int
    sectionStatus: SectionStatus
    capacity: int
    enrolled: int
    seatsRemaining: int
    courseName: str
    courseDescription: Optional[str]
    credits: int
    crn: str
    professorName: Optional[str]
    createdDate: datetime

    class Config:
        from_attributes = True


class SectionSearchItem(BaseModel):
    sectionID: int
    crn: str
    courseName: str
    courseDescription: Optional[str]
    professorName: Optional[str]
    credits: int
    capacity: int
    enrolled: int
    seatsRemaining: int
    status: SectionStatus

class ScheduleResponse(BaseModel):
    scheduleID: int
    adviseeID: int
    adviseeName: Optional[str] = None
    termID: int
    termCode: str
    termName: Optional[str] = None
    source: ScheduleSource
    status: ScheduleStatus
    createdWhen: datetime
    approvedWhen: Optional[datetime]
    rejectedWhen: Optional[datetime]
    classes: List[ClassInSchedule] = []

    class Config:
        from_attributes = True

class ScheduleListResponse(BaseModel):
    scheduleID: int
    adviseeID: int
    adviseeName: Optional[str] = None
    termID: int
    termCode: str
    termName: Optional[str] = None
    source: ScheduleSource
    status: ScheduleStatus
    createdWhen: datetime
    approvedWhen: Optional[datetime]
    rejectedWhen: Optional[datetime]
    classCount: int

    class Config:
        from_attributes = True

class PDFScrapeRequest(BaseModel):
    start_url: str
    output_path: Optional[str] = None
    max_pages: int = Field(200, ge=1, le=5000)
    delay: float = Field(0.5, ge=0)
    timeout: int = Field(20, ge=1)
    verbose: bool = False
    require_keywords: List[str] = []

class PDFScrapeResponse(BaseModel):
    success: bool
    exit_code: int
    output_path: str
    stdout: str
    stderr: str
    duration_seconds: float


class TermResponse(BaseModel):
    termID: int
    code: str
    startDate: datetime
    endDate: datetime

# ---------- Utils ------------
def _resolve_output_path(requested: Optional[str]) -> Path:
    if requested:
        path = Path(requested)
    else:
        path = Path(f"pdf_results/output_{int(time.time())}.json")
    if not path.is_absolute():
        path = (API_WORKDIR / path).resolve()
    return path

def verify_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
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
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "degraded", "error": str(e)}

@app.get("/me")
def me(user=Depends(verify_token)):
    return {"user": user}

@app.get("/db")
def test_db(user=Depends(verify_token)):
    with engine.connect() as conn:
        ver = conn.execute(text("SELECT VERSION()")).scalar_one()
    return {"authenticated_user": user.get("sub"), "db_version": ver}


@app.get("/terms", response_model=List[TermResponse])
def list_terms(
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    user=Depends(verify_token),
):
    params = {"offset": skip, "limit": limit}
    filters = []

    if search:
        filters.append("code LIKE :search")
        params["search"] = f"%{search}%"

    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = " WHERE " + where_clause

    query = f"""
        SELECT termID, code, startDate, endDate
        FROM terms
        {where_clause}
        ORDER BY startDate DESC
        LIMIT :limit OFFSET :offset
    """
    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().all()
        return [dict(row) for row in rows]

# ---------- PDF SCRAPER (PATCHED) ----------
@app.post("/pdf-scraper", response_model=PDFScrapeResponse)
@app.post("/api/pdf-scraper", response_model=PDFScrapeResponse, include_in_schema=False)
def trigger_pdf_scraper(payload: PDFScrapeRequest, user=Depends(verify_token)):
    output_path = _resolve_output_path(payload.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    start_time = time.monotonic()

    try:
        results = run_pdf_scraper(
            start_url=payload.start_url,
            max_pages=payload.max_pages,
            delay=payload.delay,
            keywords=payload.require_keywords,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF scraper failed: {exc}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    duration = time.monotonic() - start_time

    return PDFScrapeResponse(
        success=True,
        exit_code=0,
        output_path=str(output_path),
        stdout="OK",
        stderr="",
        duration_seconds=duration,
    )

# ---------------- SCHEDULE QUERIES ----------------

SCHEDULE_DETAIL_SQL = """
SELECT s.scheduleID,
       s.adviseeID,
       u.username AS adviseeName,
       s.termID,
       t.code AS termCode,
        t.code AS termName,
       s.source,
       s.status,
       s.createdWhen,
       s.approvedWhen,
       s.rejectedWhen
FROM schedules s
JOIN terms t ON t.termID = s.termID
JOIN adviseeProfile ap ON ap.adviseeID = s.adviseeID
JOIN users u ON u.userID = ap.userID
WHERE s.scheduleID = :schedule_id
"""

CLASS_LIST_SQL = """
SELECT c.classID,
       c.sectionID,
       c.createdDate,
       sec.capacity,
       sec.enrolled,
       sec.status AS sectionStatus,
       GREATEST(sec.capacity - sec.enrolled, 0) AS seatsRemaining,
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
        schedule = conn.execute(
            text(SCHEDULE_DETAIL_SQL), {"schedule_id": schedule_id}
        ).mappings().first()
        if not schedule:
            raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

        classes = conn.execute(
            text(CLASS_LIST_SQL), {"schedule_id": schedule_id}
        ).mappings().all()

        schedule = dict(schedule)
        schedule["classes"] = [dict(row) for row in classes]
        return schedule

def _ensure_term_exists(conn, term_id: int):
    term = conn.execute(
        text("SELECT termID FROM terms WHERE termID = :term_id"),
        {"term_id": term_id},
    ).first()
    if not term:
        raise HTTPException(status_code=404, detail=f"Term {term_id} not found")


def _lookup_schedule(conn, schedule_id: int):
    schedule = conn.execute(
        text("SELECT scheduleID, termID, status FROM schedules WHERE scheduleID = :sid"),
        {"sid": schedule_id},
    ).mappings().first()
    if not schedule:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
    return schedule


def _search_sections_for_schedule(conn, schedule, search: Optional[str], limit: int):
    filters = ["sec.termID = :term_id", "sec.status = :status"]
    params = {"term_id": schedule["termID"], "status": SectionStatus.OPEN.value, "limit": limit}

    if search:
        filters.append(
            "(co.courseName LIKE :q OR co.description LIKE :q OR sec.crn LIKE :q)"
        )
        params["q"] = f"%{search}%"

    query = f"""
        SELECT sec.sectionID,
               sec.crn,
               sec.capacity,
               sec.enrolled,
               sec.status,
               co.courseName,
               co.description AS courseDescription,
               co.credits,
               sec.professorName,
               GREATEST(sec.capacity - sec.enrolled, 0) AS seatsRemaining
        FROM sections sec
        JOIN courses co ON co.courseID = sec.courseID
        WHERE {' AND '.join(filters)}
        ORDER BY co.courseName ASC, sec.crn ASC
        LIMIT :limit
    """
    rows = conn.execute(text(query), params).mappings().all()
    return [dict(row) for row in rows]

# ------------- CRUD & Routes for schedules remain unchanged -------------

@app.get("/schedules", response_model=List[ScheduleListResponse])
def list_schedules(
    advisee_id: Optional[int] = None,
    advisee_name: Optional[str] = None,
    term_id: Optional[int] = None,
    term_name: Optional[str] = None,
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
    if advisee_name:
        filters.append("LOWER(u.username) LIKE :advisee_name")
        params["advisee_name"] = f"%{advisee_name.lower()}%"
    if term_id is not None:
        filters.append("s.termID = :term_id")
        params["term_id"] = term_id
    if term_name:
        filters.append("LOWER(t.code) LIKE :term_name")
        params["term_name"] = f"%{term_name.lower()}%"
    if status is not None:
        filters.append("s.status = :status")
        params["status"] = status.value

    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = " AND " + where_clause

    query = f"""
    SELECT s.scheduleID,
           s.adviseeID,
           u.username AS adviseeName,
           s.termID,
           t.code AS termCode,
           t.code AS termName,
           s.source,
           s.status,
           s.createdWhen,
           s.approvedWhen,
           s.rejectedWhen,
           (SELECT COUNT(*) FROM classes c WHERE c.scheduleID = s.scheduleID) AS classCount
    FROM schedules s
    JOIN terms t ON t.termID = s.termID
    JOIN adviseeProfile ap ON ap.adviseeID = s.adviseeID
    JOIN users u ON u.userID = ap.userID
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


@app.get(
    "/schedules/{schedule_id}/sections",
    response_model=List[SectionSearchItem],
    summary="List available sections for a schedule's term",
)
def list_sections_for_schedule(
    schedule_id: int,
    search: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    user=Depends(verify_token),
):
    with engine.connect() as conn:
        schedule = _lookup_schedule(conn, schedule_id)
        sections = _search_sections_for_schedule(conn, schedule, search, limit)
        return sections


@app.post("/schedules", response_model=ScheduleResponse, status_code=201)
def create_schedule(payload: ScheduleCreate, user=Depends(verify_token)):
    now = datetime.utcnow()
    with engine.begin() as conn:
        _ensure_term_exists(conn, payload.termID)
        result = conn.execute(
            text(
                """
                INSERT INTO schedules
                (adviseeID, termID, source, status, createdWhen, approvedWhen, rejectedWhen)
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
    requires_class_check = payload.status == ScheduleStatus.APPROVED

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

        if requires_class_check:
            class_count = conn.execute(
                text("SELECT COUNT(*) FROM classes WHERE scheduleID = :schedule_id"),
                {"schedule_id": schedule_id},
            ).scalar_one()
            if class_count == 0:
                raise HTTPException(
                    status_code=400, detail="Cannot approve a schedule with no classes"
                )

        conn.execute(
            text(f"UPDATE schedules SET {set_clause} WHERE scheduleID = :schedule_id"),
            params,
        )

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

        conn.execute(
            text("DELETE FROM classes WHERE scheduleID = :schedule_id"),
            {"schedule_id": schedule_id},
        )
        conn.execute(
            text("DELETE FROM schedules WHERE scheduleID = :schedule_id"),
            {"schedule_id": schedule_id},
        )

    return {"message": f"Schedule {schedule_id} deleted successfully"}

@app.post("/schedules/{schedule_id}/classes", response_model=ScheduleResponse)
def add_class_to_schedule(schedule_id: int, payload: AddClassRequest, user=Depends(verify_token)):
    with engine.begin() as conn:
        schedule = _lookup_schedule(conn, schedule_id)

        if schedule["status"] != ScheduleStatus.DRAFT.value:
            raise HTTPException(
                status_code=400, detail="Only DRAFT schedules can be modified"
            )

        section = conn.execute(
            text(
                "SELECT sectionID, termID, capacity, enrolled, status "
                "FROM sections WHERE sectionID = :sec"
            ),
            {"sec": payload.sectionID},
        ).mappings().first()

        if not section:
            raise HTTPException(status_code=404, detail=f"Section {payload.sectionID} not found")

        if section["status"] != SectionStatus.OPEN.value:
            raise HTTPException(
                status_code=400,
                detail=f"Section {payload.sectionID} is not open for scheduling",
            )

        if section["termID"] != schedule["termID"]:
            raise HTTPException(
                status_code=400,
                detail=f"Section term {section['termID']} does not match schedule term {schedule['termID']}",
            )

        if section["enrolled"] >= section["capacity"]:
            raise HTTPException(
                status_code=400,
                detail=f"Section {payload.sectionID} is already full",
            )

        existing = conn.execute(
            text("SELECT 1 FROM classes WHERE scheduleID = :sid AND sectionID = :sec"),
            {"sid": schedule_id, "sec": payload.sectionID},
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Section {payload.sectionID} already exists in schedule {schedule_id}",
            )

        conn.execute(
            text(
                "INSERT INTO classes (sectionID, scheduleID, createdDate) "
                "VALUES (:sec, :sid, :created)"
            ),
            {
                "sec": payload.sectionID,
                "sid": schedule_id,
                "created": datetime.utcnow(),
            },
        )

        conn.execute(
            text(
                "UPDATE sections SET enrolled = enrolled + 1 "
                "WHERE sectionID = :sec AND enrolled < capacity"
            ),
            {"sec": payload.sectionID},
        )

    return _schedule_with_classes(schedule_id)

@app.delete("/schedules/{schedule_id}/classes/{class_id}", response_model=ScheduleResponse)
def remove_class_from_schedule(schedule_id: int, class_id: int, user=Depends(verify_token)):
    with engine.begin() as conn:
        cls = conn.execute(
            text(
                """
                SELECT c.sectionID, s.status AS scheduleStatus
                FROM classes c
                JOIN schedules s ON s.scheduleID = c.scheduleID
                WHERE c.classID = :cid AND c.scheduleID = :sid
                """
            ),
            {"cid": class_id, "sid": schedule_id},
        ).mappings().first()

        if not cls:
            raise HTTPException(
                status_code=404,
                detail=f"Class {class_id} not found in schedule {schedule_id}",
            )

        if cls["scheduleStatus"] != ScheduleStatus.DRAFT.value:
            raise HTTPException(
                status_code=400, detail="Only DRAFT schedules can be modified"
            )

        conn.execute(
            text(
                "UPDATE sections SET enrolled = CASE WHEN enrolled > 0 THEN enrolled - 1 ELSE 0 END "
                "WHERE sectionID = :sec"
            ),
            {"sec": cls["sectionID"]},
        )

        conn.execute(
            text(
                "DELETE FROM classes WHERE classID = :cid AND scheduleID = :sid"
            ),
            {"cid": class_id, "sid": schedule_id},
        )

    return _schedule_with_classes(schedule_id)


COURSE_LINE_REGEX = re.compile(
    r"""
    (?P<code>[A-Z]{2,4}\s?\d{3,4})       # Course code: CS 2023
    [^\S\r\n]+                           # whitespace
    (?P<title>[A-Za-z][A-Za-z0-9\s,&\-/]+?)   # Title
    [^\S\r\n]+
    (?P<credits>\d+)                     # Credits
    (?:\s*(?:credit|credits|cr))?        # optional word
    """,
    re.VERBOSE
)

TERM_REGEX = re.compile(
    r"(Fall|Spring|Summer|Winter)\s+(\d{4})",
    re.IGNORECASE
)


def parse_courses_from_text(text: str):
    """Extract completed courses + detect term blocks"""
    results = []
    current_term = None

    lines = text.splitlines()

    for line in lines:
        term_match = TERM_REGEX.search(line)
        if term_match:
            current_term = f"{term_match.group(1)} {term_match.group(2)}"

        match = COURSE_LINE_REGEX.search(line)
        if match:
            data = match.groupdict()
            results.append({
                "code": data["code"].upper(),
                "title": data["title"].strip(),
                "credits": int(data["credits"]),
                "term": current_term
            })

    return results


# ============================================================
# Import PDF → Context → Validate
# ============================================================

async def save_context_for_advisee(advisee_id: int, context: dict):
    """Persist degree plan context to DB."""
    query = text("""
        INSERT INTO degreeplan_context (adviseeID, contextJSON, updatedWhen)
        VALUES (:adviseeID, :context, UTC_TIMESTAMP())
        ON DUPLICATE KEY UPDATE
            contextJSON = VALUES(contextJSON),
            updatedWhen = UTC_TIMESTAMP()
    """)

    with engine.begin() as conn:
        conn.execute(query, {
            "adviseeID": advisee_id,
            "context": json.dumps(context)
        })


async def run_validation_for_advisee(advisee_id: int):
    """Execute existing validation pipeline."""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT requirementSetID FROM advisee_requirements WHERE adviseeID = :id"),
            {"id": advisee_id}
        ).mappings().first()

        if not result:
            raise HTTPException(status_code=400, detail="Advisee does not have a linked requirement set.")

        req_set_id = result["requirementSetID"]

    # Call existing validator
    from degree_validation.engine import run_validation
    return run_validation(advisee_id, req_set_id)


@app.post("/advisees/{advisee_id}/import-degreework-pdf")
async def import_degreework_pdf(advisee_id: int, payload: dict, user=Depends(verify_token)):
    """
    1. Scrape PDF
    2. Parse completed courses
    3. Save degreeplan_context
    4. Trigger validation
    """
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' field.")

    scraped = run_pdf_scraper(url)
    all_text = " ".join(pdf["text"] for pdf in scraped.values())

    completed_courses = parse_courses_from_text(all_text)

    await save_context_for_advisee(advisee_id, {
        "completedCourses": completed_courses
    })

    validation_result = await run_validation_for_advisee(advisee_id)

    return {
        "importedCourses": completed_courses,
        "validation": validation_result
    }
