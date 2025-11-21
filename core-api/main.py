from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
import re

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

PDF_RESULTS_DIR = Path(os.getenv("PDF_RESULTS_DIR", "/code/pdf_results")).resolve()
PDF_RESULTS_GLOB = os.getenv("PDF_RESULTS_GLOB", "output_*.txt")

DEGREE_CATEGORY_DEFINITIONS = [
    {
        "slug": "english_composition",
        "label": "English composition requirement",
        "match": ["english composition", "composition requirement"],
        "course_keywords": ["english", "composition", "rhetoric", "writing"],
    },
    {
        "slug": "mathematics",
        "label": "Mathematics requirement",
        "match": ["mathematics requirement", "math requirement"],
        "course_keywords": ["math", "mathematics", "algebra", "calculus", "statistics"],
    },
    {
        "slug": "speech",
        "label": "Speech communication requirement",
        "match": ["speech", "spch", "communication requirement"],
        "course_keywords": ["speech", "communication", "public speaking"],
    },
    {
        "slug": "lab_science",
        "label": "Lab Science requirement",
        "match": ["lab science requirement", "laboratory science"],
        "course_keywords": ["biology", "chemistry", "physics", "geology", "astronomy", "lab"],
    },
    {
        "slug": "fine_arts",
        "label": "Fine Arts requirement",
        "match": ["fine arts requirement", "fine art requirement"],
        "course_keywords": ["art", "music", "theatre", "theater", "dance"],
    },
    {
        "slug": "humanities",
        "label": "Humanities requirement",
        "match": ["humanities requirement", "humanities"],
        "course_keywords": ["humanities", "philosophy", "literature", "ethics"],
    },
    {
        "slug": "history_government",
        "label": "History/Government requirement",
        "match": ["history/government", "history requirement", "government requirement"],
        "course_keywords": ["history", "government", "political", "civics"],
    },
    {
        "slug": "social_sciences",
        "label": "Social Sciences requirement",
        "match": ["social sciences requirement", "social science requirement"],
        "course_keywords": ["psychology", "sociology", "anthropology", "economics", "political science"],
    },
    {
        "slug": "institutional",
        "label": "Institutional requirement/advisor elective",
        "match": ["institutional requirement", "advisor elective"],
        "course_keywords": ["institutional", "finance", "personal finance", "ita 1003"],
    },
    {
        "slug": "directed_electives",
        "label": "Directed electives",
        "match": ["directed electives", "directed elective"],
        "course_keywords": [],
    },
    {
        "slug": "state_core",
        "label": "State General Education Core Requirements",
        "match": ["state general education core"],
        "course_keywords": [],
        "uses_overall_hours": True,
    },
    {
        "slug": "total_hours",
        "label": "Total Hours",
        "match": ["total hours"],
        "course_keywords": [],
        "uses_overall_hours": True,
        "is_total": True,
    },
]

CATEGORY_BY_SLUG = {item["slug"]: item for item in DEGREE_CATEGORY_DEFINITIONS}
DEFAULT_ELECTIVE_SLUG = "directed_electives"

HOURS_INLINE_PATTERN = re.compile(
    r"^(?P<label>.+?)\s*[:\-]?\s*(?P<min>\d+)(?:-(?P<max>\d+))?\s+(?:hours|hrs)\b",
    re.IGNORECASE,
)
HOURS_ONLY_PATTERN = re.compile(r"^(?P<min>\d+)(?:-(?P<max>\d+))?\s+(?:hours|hrs)\b", re.IGNORECASE)
TOTAL_HOURS_PATTERN = re.compile(r"^total\s+hours[:\s]*(?P<min>\d+)", re.IGNORECASE)


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


class RequirementStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class AdviseeProfileInfo(BaseModel):
    adviseeID: int
    studentName: Optional[str]
    email: Optional[str]
    major: Optional[str]
    degreePlan: Optional[str]
    classification: Optional[str]
    gpa: Optional[float]
    creditsCompleted: Optional[int]


class DegreePlanInfo(BaseModel):
    degreePlanID: Optional[int]
    name: Optional[str]
    catalog: Optional[str]
    status: Optional[str]
    updatedWhen: Optional[datetime]


class DocumentInfo(BaseModel):
    title: str
    sourcePath: str
    lastModified: Optional[datetime]
    requirementCount: int


class RequirementCourse(BaseModel):
    courseID: Optional[int]
    courseName: str
    credits: Optional[float]
    source: str
    status: Optional[str]
    scheduleID: Optional[int]
    sectionID: Optional[int]
    termCode: Optional[str]
    grade: Optional[str]


class RequirementProgress(BaseModel):
    key: str
    displayName: str
    requiredHours: float
    maxHours: Optional[float]
    completedHours: float
    inProgressHours: float
    projectedHours: float
    remainingHours: float
    projectedRemainingHours: float
    status: RequirementStatus
    matchedCourses: List[RequirementCourse] = Field(default_factory=list)
    notes: Optional[str] = None


class DegreeValidationSummary(BaseModel):
    totalRequiredHours: float
    totalCompletedHours: float
    totalInProgressHours: float
    totalProjectedHours: float
    overallStatus: RequirementStatus


class DegreePlanValidationResponse(BaseModel):
    advisee: AdviseeProfileInfo
    degreePlan: Optional[DegreePlanInfo]
    document: DocumentInfo
    summary: DegreeValidationSummary
    requirements: List[RequirementProgress]
    unmatchedCourses: List[RequirementCourse] = Field(default_factory=list)

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


# --- Degree validation helpers ------------------------------------------------

def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", (value or "").lower()).strip("_")
    return cleaned or "requirement"


def _looks_like_requirement_label(line: str) -> bool:
    lowered = line.lower()
    if not lowered or len(lowered) < 4:
        return False
    if lowered.startswith("note"):
        return False
    keywords = [
        "requirement",
        "elective",
        "institutional",
        "directed",
        "general education",
    ]
    return any(keyword in lowered for keyword in keywords)


def _resolve_pdf_file(pdf_path: Optional[str]) -> Path:
    if pdf_path:
        candidate = Path(pdf_path)
        if not candidate.is_absolute():
            candidate = PDF_RESULTS_DIR / candidate
        candidate = candidate.resolve()
        if not candidate.exists():
            raise HTTPException(status_code=404, detail=f"PDF output file not found at {candidate}")
        return candidate

    if not PDF_RESULTS_DIR.exists():
        raise HTTPException(
            status_code=404,
            detail=f"PDF results directory {PDF_RESULTS_DIR} does not exist. Run the scraper first.",
        )

    files = sorted(PDF_RESULTS_DIR.glob(PDF_RESULTS_GLOB or "*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise HTTPException(status_code=404, detail=f"No PDF scrape outputs found in {PDF_RESULTS_DIR}")
    return files[0]


def _load_pdf_documents(pdf_file: Path) -> List[Dict[str, str]]:
    documents: List[Dict[str, str]] = []
    current_lines: List[str] = []
    title: Optional[str] = None
    inside = False

    with pdf_file.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            if line.startswith("----- PDF") and "START" in line:
                inside = True
                current_lines = []
                title = None
                continue
            if line.startswith("----- PDF") and "END" in line:
                if current_lines:
                    documents.append(
                        {
                            "title": title or f"PDF {len(documents) + 1}",
                            "text": "\n".join(current_lines).strip(),
                        }
                    )
                inside = False
                continue
            if not inside:
                continue
            if line.startswith("Title:"):
                possible = line.split("Title:", 1)[1].strip()
                if possible:
                    title = possible
                continue
            current_lines.append(line)

    if not documents and current_lines:
        documents.append(
            {
                "title": title or pdf_file.stem,
                "text": "\n".join(current_lines).strip(),
            }
        )
    return documents


def _select_document(documents: List[Dict[str, str]], document_title: Optional[str]) -> Dict[str, str]:
    if not documents:
        raise HTTPException(status_code=404, detail="PDF output did not contain any degree plan text.")

    if document_title:
        normalized = document_title.lower()
        for doc in documents:
            if normalized in (doc.get("title") or "").lower():
                return doc
    return documents[0]


def _extract_raw_requirements(text_block: str) -> List[Dict[str, object]]:
    requirements: List[Dict[str, object]] = []
    pending_labels: List[str] = []
    order = 0
    for raw_line in text_block.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        total_match = TOTAL_HOURS_PATTERN.match(line)
        if total_match:
            hours = float(total_match.group("min"))
            requirements.append(
                {
                    "name": "Total Hours",
                    "min_hours": hours,
                    "max_hours": hours,
                    "order": order,
                    "is_total": True,
                }
            )
            order += 1
            continue

        inline_match = HOURS_INLINE_PATTERN.match(line)
        if inline_match:
            label = inline_match.group("label").strip()
            hours = float(inline_match.group("min"))
            max_hours = inline_match.group("max")
            name = label or (pending_labels.pop(0) if pending_labels else "Requirement")
            requirements.append(
                {
                    "name": name.strip(": "),
                    "min_hours": hours,
                    "max_hours": float(max_hours) if max_hours else None,
                    "order": order,
                    "is_total": False,
                }
            )
            order += 1
            continue

        hours_match = HOURS_ONLY_PATTERN.match(line)
        if hours_match and pending_labels:
            label = pending_labels.pop(0)
            hours = float(hours_match.group("min"))
            max_hours = hours_match.group("max")
            requirements.append(
                {
                    "name": label.strip(": "),
                    "min_hours": hours,
                    "max_hours": float(max_hours) if max_hours else None,
                    "order": order,
                    "is_total": False,
                }
            )
            order += 1
            continue

        if _looks_like_requirement_label(line):
            pending_labels.append(line.rstrip(":"))

    return requirements


def _canonicalize_requirement(name: str) -> Dict[str, object]:
    normalized = (name or "").lower()
    for definition in DEGREE_CATEGORY_DEFINITIONS:
        if any(keyword in normalized for keyword in definition.get("match", [])):
            return definition
    return {
        "slug": _slugify(name),
        "label": name,
        "match": [],
        "course_keywords": [],
    }


def _extract_keywords(label: str) -> List[str]:
    return [token for token in re.split(r"[^a-z]+", (label or "").lower()) if len(token) > 3]


def _build_requirement_entries(raw_requirements: List[Dict[str, object]]) -> List[Dict[str, object]]:
    grouped: Dict[str, Dict[str, object]] = {}
    for entry in raw_requirements:
        name = entry.get("name") or "Requirement"
        definition = _canonicalize_requirement(name)
        slug = definition["slug"]
        existing = grouped.get(slug)
        min_hours = float(entry.get("min_hours") or 0.0)
        max_hours = entry.get("max_hours")
        is_total = bool(entry.get("is_total") or definition.get("is_total"))
        uses_overall = bool(definition.get("uses_overall_hours"))

        if existing:
            existing["required_hours"] += min_hours
            if max_hours:
                existing["max_hours"] = (existing["max_hours"] or 0) + max_hours
            existing["is_total"] = existing["is_total"] or is_total
            existing["uses_overall_hours"] = existing["uses_overall_hours"] or uses_overall
            existing["source_names"].append(name)
        else:
            grouped[slug] = {
                "slug": slug,
                "display": definition.get("label") or name,
                "required_hours": min_hours,
                "max_hours": max_hours,
                "order": entry.get("order", len(grouped)),
                "is_total": is_total,
                "uses_overall_hours": uses_overall,
                "definition": definition,
                "source_names": [name],
                "matched_courses": [],
                "completed_hours": 0.0,
                "in_progress_hours": 0.0,
            }

    return sorted(grouped.values(), key=lambda item: item["order"])


def _categorize_course(course_name: str, course_description: Optional[str]) -> Optional[str]:
    searchable = f"{course_name or ''} {(course_description or '')}".lower()
    for definition in DEGREE_CATEGORY_DEFINITIONS:
        for keyword in definition.get("course_keywords", []):
            if keyword and keyword.lower() in searchable:
                return definition["slug"]
    return None


def _assign_course(requirement: Dict[str, object], course: Dict[str, object]):
    credits = float(course.get("credits") or 0)
    requirement["matched_courses"].append(course)
    if course.get("source") == "COMPLETED":
        requirement["completed_hours"] += credits
    else:
        requirement["in_progress_hours"] += credits


def _map_courses_to_requirements(requirements: List[Dict[str, object]], courses: List[Dict[str, object]]):
    unmatched: List[Dict[str, object]] = []
    directed_req = next((req for req in requirements if req["slug"] == DEFAULT_ELECTIVE_SLUG), None)

    for course in courses:
        assigned = False
        category_slug = _categorize_course(course.get("courseName"), course.get("courseDescription"))
        candidate_order = requirements

        if category_slug:
            candidate_order = sorted(
                requirements,
                key=lambda req: 0 if req["slug"] == category_slug else 1,
            )

        course_text = f"{course.get('courseName', '')} {(course.get('courseDescription') or '')}".lower()

        for req in candidate_order:
            if req["slug"] != category_slug and category_slug:
                continue
            keywords = req["definition"].get("course_keywords") or _extract_keywords(req["display"])
            if not keywords and not req.get("uses_overall_hours"):
                continue
            if req.get("uses_overall_hours"):
                # overall requirements will be filled later
                continue
            if keywords and not any(keyword in course_text for keyword in keywords):
                continue
            _assign_course(req, course)
            assigned = True
            break

        if not assigned and directed_req and course_text:
            _assign_course(directed_req, course)
            assigned = True

        if not assigned:
            unmatched.append(course)

    return unmatched


def _fetch_advisee_profile(conn, advisee_id: int) -> Dict[str, object]:
    row = conn.execute(
        text(
            """
        SELECT ap.adviseeID,
               ap.major,
               ap.degree_plan,
               ap.classification,
               ap.gpa,
               ap.credits_completed,
               u.username,
               u.email
        FROM adviseeProfile ap
        LEFT JOIN users u ON u.userID = ap.userID
        WHERE ap.adviseeID = :advisee_id
        """
        ),
        {"advisee_id": advisee_id},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail=f"Advisee {advisee_id} not found")
    return dict(row)


def _fetch_degree_plan(conn, advisee_id: int) -> Optional[Dict[str, object]]:
    row = conn.execute(
        text(
            """
        SELECT degreePlanID,
               name,
               catalog,
               status,
               updatedWhen
        FROM degreePlan
        WHERE adviseeID = :advisee_id
        ORDER BY
            CASE status WHEN 'Active' THEN 1 WHEN 'Draft' THEN 2 ELSE 3 END,
            updatedWhen DESC
        LIMIT 1
        """
        ),
        {"advisee_id": advisee_id},
    ).mappings().first()
    return dict(row) if row else None


def _fetch_completed_courses(conn, advisee_id: int) -> List[Dict[str, object]]:
    rows = conn.execute(
        text(
            """
        SELECT e.enrollmentID,
               e.sectionID,
               e.courseID,
               e.status,
               e.grade,
               e.creditsEarned,
               c.courseName,
               c.description,
               c.credits,
               sec.termID,
               t.code AS termCode
        FROM enrollments e
        JOIN courses c ON c.courseID = e.courseID
        LEFT JOIN sections sec ON sec.sectionID = e.sectionID
        LEFT JOIN terms t ON t.termID = sec.termID
        WHERE e.adviseeID = :advisee_id
        """
        ),
        {"advisee_id": advisee_id},
    ).mappings().all()

    results = []
    for row in rows:
        credits = row.get("creditsEarned") or row.get("credits") or 0
        source = "COMPLETED" if row.get("status") == "COMPLETED" else "IN_PROGRESS"
        results.append(
            {
                "courseID": row.get("courseID"),
                "courseName": row.get("courseName"),
                "courseDescription": row.get("description"),
                "credits": float(credits),
                "source": source,
                "status": row.get("status"),
                "grade": row.get("grade"),
                "scheduleID": None,
                "sectionID": row.get("sectionID"),
                "termCode": row.get("termCode"),
            }
        )
    return results


def _fetch_planned_classes(conn, advisee_id: int) -> List[Dict[str, object]]:
    rows = conn.execute(
        text(
            """
        SELECT c.classID,
               c.sectionID,
               c.scheduleID,
               sec.courseID,
               co.courseName,
               co.description,
               co.credits,
               sec.termID,
               t.code AS termCode,
               sch.status AS scheduleStatus
        FROM classes c
        JOIN schedules sch ON sch.scheduleID = c.scheduleID
        JOIN sections sec ON sec.sectionID = c.sectionID
        JOIN courses co ON co.courseID = sec.courseID
        LEFT JOIN terms t ON t.termID = sec.termID
        WHERE sch.adviseeID = :advisee_id
        """
        ),
        {"advisee_id": advisee_id},
    ).mappings().all()

    results = []
    for row in rows:
        results.append(
            {
                "courseID": row.get("courseID"),
                "courseName": row.get("courseName"),
                "courseDescription": row.get("description"),
                "credits": float(row.get("credits") or 0),
                "source": "PLANNED",
                "status": row.get("scheduleStatus"),
                "grade": None,
                "scheduleID": row.get("scheduleID"),
                "sectionID": row.get("sectionID"),
                "termCode": row.get("termCode"),
            }
        )
    return results


def _finalize_overall_requirements(
    requirements: List[Dict[str, object]],
    total_completed: float,
    total_in_progress: float,
):
    for req in requirements:
        if req.get("uses_overall_hours"):
            req["completed_hours"] = total_completed
            req["in_progress_hours"] = total_in_progress


def _serialize_requirement_courses(items: List[Dict[str, object]]) -> List[RequirementCourse]:
    serialized = []
    for item in items:
        serialized.append(
            RequirementCourse(
                courseID=item.get("courseID"),
                courseName=item.get("courseName") or "Course",
                credits=item.get("credits"),
                source=item.get("source") or "COMPLETED",
                status=item.get("status"),
                scheduleID=item.get("scheduleID"),
                sectionID=item.get("sectionID"),
                termCode=item.get("termCode"),
                grade=item.get("grade"),
            )
        )
    return serialized


def _serialize_requirements(requirements: List[Dict[str, object]]) -> List[RequirementProgress]:
    serialized: List[RequirementProgress] = []
    for req in requirements:
        projected = req["completed_hours"] + req["in_progress_hours"]
        remaining = max(0.0, req["required_hours"] - req["completed_hours"])
        projected_remaining = max(0.0, req["required_hours"] - projected)

        if req["completed_hours"] >= req["required_hours"] and req["required_hours"] > 0:
            status = RequirementStatus.COMPLETED
        elif projected > 0:
            status = RequirementStatus.IN_PROGRESS
        else:
            status = RequirementStatus.NOT_STARTED

        serialized.append(
            RequirementProgress(
                key=req["slug"],
                displayName=req["display"],
                requiredHours=req["required_hours"],
                maxHours=req.get("max_hours"),
                completedHours=round(req["completed_hours"], 2),
                inProgressHours=round(req["in_progress_hours"], 2),
                projectedHours=round(projected, 2),
                remainingHours=round(remaining, 2),
                projectedRemainingHours=round(projected_remaining, 2),
                status=status,
                matchedCourses=_serialize_requirement_courses(req["matched_courses"]),
                notes=", ".join(sorted(set(req.get("source_names", [])))),
            )
        )
    return serialized


def _build_summary(requirements: List[RequirementProgress]) -> DegreeValidationSummary:
    non_total = [req for req in requirements if req.key != "total_hours"]
    total_required = sum(req.requiredHours for req in non_total)
    total_completed = sum(req.completedHours for req in non_total)
    total_in_progress = sum(req.inProgressHours for req in non_total)
    total_projected = total_completed + total_in_progress

    total_requirement = next((req for req in requirements if req.key == "total_hours"), None)
    if total_requirement:
        total_required = max(total_required, total_requirement.requiredHours)

    if non_total:
        if all(req.status == RequirementStatus.COMPLETED for req in non_total):
            overall = RequirementStatus.COMPLETED
        elif any(req.status != RequirementStatus.NOT_STARTED for req in non_total):
            overall = RequirementStatus.IN_PROGRESS
        else:
            overall = RequirementStatus.NOT_STARTED
    else:
        overall = RequirementStatus.NOT_STARTED

    return DegreeValidationSummary(
        totalRequiredHours=round(total_required, 2),
        totalCompletedHours=round(total_completed, 2),
        totalInProgressHours=round(total_in_progress, 2),
        totalProjectedHours=round(total_projected, 2),
        overallStatus=overall,
    )


@app.get(
    "/advisees/{advisee_id}/degree-progress",
    response_model=DegreePlanValidationResponse,
)
def validate_degree_plan(
    advisee_id: int,
    document_title: Optional[str] = None,
    pdf_path: Optional[str] = None,
    user=Depends(verify_token),
):
    pdf_file = _resolve_pdf_file(pdf_path)
    documents = _load_pdf_documents(pdf_file)
    document = _select_document(documents, document_title)

    raw_requirements = _extract_raw_requirements(document.get("text", ""))
    if not raw_requirements:
        raise HTTPException(
            status_code=400,
            detail="Unable to identify degree requirements in the provided PDF output.",
        )

    requirement_entries = _build_requirement_entries(raw_requirements)

    with engine.connect() as conn:
        advisee_record = _fetch_advisee_profile(conn, advisee_id)
        degree_plan_record = _fetch_degree_plan(conn, advisee_id)
        completed_courses = _fetch_completed_courses(conn, advisee_id)
        planned_courses = _fetch_planned_classes(conn, advisee_id)

    combined_courses = completed_courses + planned_courses
    total_completed_hours = sum(course.get("credits") or 0 for course in combined_courses if course.get("source") == "COMPLETED")
    total_in_progress_hours = sum(course.get("credits") or 0 for course in combined_courses if course.get("source") != "COMPLETED")

    unmatched_courses = _map_courses_to_requirements(requirement_entries, combined_courses)
    _finalize_overall_requirements(requirement_entries, total_completed_hours, total_in_progress_hours)

    requirements_payload = _serialize_requirements(requirement_entries)
    summary = _build_summary(requirements_payload)

    file_stat = pdf_file.stat() if pdf_file.exists() else None
    document_info = DocumentInfo(
        title=document.get("title") or "Degree plan",
        sourcePath=str(pdf_file),
        lastModified=datetime.fromtimestamp(file_stat.st_mtime) if file_stat else None,
        requirementCount=len(requirements_payload),
    )

    advisee_info = AdviseeProfileInfo(
        adviseeID=advisee_record["adviseeID"],
        studentName=advisee_record.get("username"),
        email=advisee_record.get("email"),
        major=advisee_record.get("major"),
        degreePlan=advisee_record.get("degree_plan"),
        classification=advisee_record.get("classification"),
        gpa=advisee_record.get("gpa"),
        creditsCompleted=advisee_record.get("credits_completed"),
    )

    degree_plan_info = (
        DegreePlanInfo(
            degreePlanID=degree_plan_record.get("degreePlanID"),
            name=degree_plan_record.get("name"),
            catalog=degree_plan_record.get("catalog"),
            status=degree_plan_record.get("status"),
            updatedWhen=degree_plan_record.get("updatedWhen"),
        )
        if degree_plan_record
        else None
    )

    return DegreePlanValidationResponse(
        advisee=advisee_info,
        degreePlan=degree_plan_info,
        document=document_info,
        summary=summary,
        requirements=requirements_payload,
        unmatchedCourses=_serialize_requirement_courses(unmatched_courses),
    )
