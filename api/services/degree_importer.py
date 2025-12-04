# services/degree_importer.py
from datetime import datetime
from typing import Optional, Sequence

import requests
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.degree_plan import (
    DegreeRequirementSet,
    AdviseeDegreeContext,
    DegreePlanValidation,
    ValidationStatus,
    ValidationRunType,
)
from pdf_scraper.scrape_pdfs import run_pdf_scraper
from services.pdf_parser import extract_courses, extract_program_info


def _ensure_major_exists(db: Session, program_code: str, program_name: str) -> None:
    if not program_code:
        return
    exists = db.execute(
        text("SELECT 1 FROM majors WHERE programCode = :code LIMIT 1"),
        {"code": program_code},
    ).scalar()
    if exists:
        return

    degree_type = (program_code.split("-", 1)[0] or "MAJOR").upper()
    try:
        db.execute(
            text(
                """
                INSERT INTO majors (programCode, programName, degreeType, college, isActive, createdAt, updatedAt)
                VALUES (:code, :name, :degree_type, NULL, 1, NOW(), NOW())
                """
            ),
            {
                "code": program_code,
                "name": program_name or program_code,
                "degree_type": degree_type[:32] or "MAJOR",
            },
        )
        db.commit()
    except IntegrityError:
        db.rollback()


def _update_advisee_program(
    db: Session, advisee_id: int, program_code: str, program_name: str
) -> None:
    if not program_code:
        return
    db.execute(
        text(
            """
            UPDATE adviseeProfile
            SET majorCode = :code,
                degree_plan = :code
            WHERE adviseeID = :advisee_id
            """
        ),
        {"code": program_code, "advisee_id": advisee_id},
    )
    db.commit()


def _normalize_completed_courses(raw_courses):
    normalized = []
    for idx, course in enumerate(raw_courses or []):
        credits = course.get("credits")
        try:
            credits_value = float(credits)
        except (TypeError, ValueError):
            credits_value = 0.0
        if credits_value <= 0:
            credits_value = 3.0
        normalized.append(
            {
                "code": course.get("code") or f"COURSE-{idx+1}",
                "title": course.get("title"),
                "credits": credits_value,
                "term": course.get("term"),
                "status": course.get("status") or "COMPLETED",
            }
        )
    return normalized


def _calculate_total_requirement(courses) -> float:
    total = 0.0
    for course in courses or []:
        try:
            total += float(course.get("credits", 0) or 0)
        except (TypeError, ValueError):
            total += 0.0
    return total


def _build_requirement_groups(program_name: str, courses):
    required = _calculate_total_requirement(courses)
    return [
        {
            "id": "auto-import",
            "title": program_name,
            "requiredCredits": required or 1,
            "description": "Auto-generated from degree audit import",
            "courses": courses,
        }
    ]


def import_degree_plan_from_pdf_url(
    db: Session,
    advisee_id: int,
    pdf_url: str,
    required_keywords: Optional[Sequence[str]] = None,
    create_validation: bool = True,
):
    normalized = (pdf_url or "").strip()
    if not normalized:
        raise Exception("Missing pdfUrl")

    lower = normalized.lower()
    if lower.endswith(".pdf"):
        try:
            resp = requests.get(normalized, timeout=60)
            resp.raise_for_status()
        except Exception as exc:
            raise Exception(f"Failed to download PDF: {exc}")

        return import_degree_plan_from_pdf_bytes(
            db,
            advisee_id,
            resp.content,
            source_label=normalized,
            note_prefix=f"Imported from PDF: {normalized}",
        )

    # 1. SCRAPE PDF
    keyword_list = [
        kw.strip()
        for kw in (required_keywords or [])
        if isinstance(kw, str) and kw.strip()
    ] or None

    result = run_pdf_scraper(normalized, max_pages=3, keywords=keyword_list)
    if not result:
        raise Exception("No PDF found at provided URL")

    # Pick first PDF found
    pdf = list(result.values())[0]
    text = pdf["text"]

    # 2. PARSE PROGRAM INFO
    programName, catalogYear = extract_program_info(text)
    program_code = (programName or "UNKNOWN").replace(" ", "-").upper()
    _ensure_major_exists(db, program_code, programName)
    _update_advisee_program(db, advisee_id, program_code, programName)

    # 3. PARSE COMPLETED COURSES
    completed = _normalize_completed_courses(extract_courses(text))

    # 4. FIND OR CREATE REQUIREMENT SET
    requirement_set = (
        db.query(DegreeRequirementSet)
        .filter(
            DegreeRequirementSet.programCode == program_code,
            DegreeRequirementSet.catalogYear == catalogYear
        )
        .first()
    )

    if not requirement_set:
        now = datetime.utcnow()
        requirement_set = DegreeRequirementSet(
            programCode=program_code,
            catalogYear=catalogYear,
            programName=programName,
            totalCredits=_calculate_total_requirement(completed) or 1,
            requirementData=_build_requirement_groups(programName, completed),
            sourceDocument=normalized,
            createdAt=now,
            updatedAt=now,
        )
        db.add(requirement_set)
        try:
            db.commit()
            db.refresh(requirement_set)
        except IntegrityError:
            db.rollback()
            requirement_set = (
                db.query(DegreeRequirementSet)
                .filter(
                    DegreeRequirementSet.programCode == program_code,
                    DegreeRequirementSet.catalogYear == catalogYear
                )
                .first()
            )
            if not requirement_set:
                raise

    # 5. UPSERT CONTEXT
    context = (
        db.query(AdviseeDegreeContext)
        .filter(AdviseeDegreeContext.adviseeID == advisee_id)
        .first()
    )

    if not context:
        context = AdviseeDegreeContext(
            adviseeID=advisee_id,
            requirementSetID=requirement_set.requirementSetID,
            completedCourses=completed,
            notes=f"Imported from PDF: {normalized}",
            createdAt=datetime.now()
        )
        db.add(context)
    else:
        context.completedCourses = completed
        context.requirementSetID = requirement_set.requirementSetID
        context.updatedAt = datetime.now()

    db.commit()
    db.refresh(context)

    validation = None
    if create_validation:
        # 6. CREATE VALIDATION ENTRY (RUN IMMEDIATELY)
        now = datetime.utcnow()
        validation = DegreePlanValidation(
            adviseeID=advisee_id,
            contextID=context.contextID,
            requirementSetID=requirement_set.requirementSetID,
            status=ValidationStatus.RUNNING,
            runType=ValidationRunType.MANUAL,
            startedAt=datetime.now(),
            createdAt=now,
            updatedAt=now,
        )
        db.add(validation)
        db.commit()
        db.refresh(validation)

        # Placeholder validation record for the import; actual validations run separately.
        validation.issues = []
        validation.status = ValidationStatus.PASSED
        validation.completionPercent = 100.0
        validation.finishedAt = datetime.now()

        db.commit()
        db.refresh(validation)

    return {
        "requirementSet": requirement_set,
        "context": context,
        "validation": validation,
    }

def import_degree_plan_from_pdf_bytes(
    db: Session,
    advisee_id: int,
    pdf_bytes: bytes,
    source_label: str = "uploaded-pdf",
    note_prefix: Optional[str] = "Imported from uploaded PDF",
    create_validation: bool = True,
):
    if not pdf_bytes:
        raise Exception("Uploaded PDF file is empty")

    # --- 1. Extract text from PDF bytes ---
    try:
        from pdfminer.high_level import extract_text
        from io import BytesIO
        text = extract_text(BytesIO(pdf_bytes))
    except Exception as e:
        raise Exception(f"Failed to read PDF: {e}")

    if not text or len(text.strip()) == 0:
        raise Exception("Could not extract text from PDF")

    # --- 2. Parse Program Info ---
    programName, catalogYear = extract_program_info(text)
    program_code = (programName or "UNKNOWN").replace(" ", "-").upper()
    _ensure_major_exists(db, program_code, programName)
    _update_advisee_program(db, advisee_id, program_code, programName)

    # --- 3. Parse Completed Courses ---
    completed = _normalize_completed_courses(extract_courses(text))

    # --- 4. Find or Create Requirement Set ---
    requirement_set = (
        db.query(DegreeRequirementSet)
        .filter(
            DegreeRequirementSet.programCode == program_code,
            DegreeRequirementSet.catalogYear == catalogYear
        )
        .first()
    )

    if not requirement_set:
        now = datetime.utcnow()
        requirement_set = DegreeRequirementSet(
            programCode=program_code,
            catalogYear=catalogYear,
            programName=programName,
            totalCredits=_calculate_total_requirement(completed) or 1,
            requirementData=_build_requirement_groups(programName, completed),
            sourceDocument=source_label,
            createdAt=now,
            updatedAt=now,
        )
        db.add(requirement_set)
        try:
            db.commit()
            db.refresh(requirement_set)
        except IntegrityError:
            db.rollback()
            requirement_set = (
                db.query(DegreeRequirementSet)
                .filter(
                    DegreeRequirementSet.programCode == program_code,
                    DegreeRequirementSet.catalogYear == catalogYear
                )
                .first()
            )
            if not requirement_set:
                raise

    # --- 5. Upsert Context ---
    context = (
        db.query(AdviseeDegreeContext)
        .filter(AdviseeDegreeContext.adviseeID == advisee_id)
        .first()
    )

    if not context:
        context = AdviseeDegreeContext(
            adviseeID=advisee_id,
            requirementSetID=requirement_set.requirementSetID,
            completedCourses=completed,
            notes=note_prefix,
            createdAt=datetime.now()
        )
        db.add(context)
    else:
        context.completedCourses = completed
        context.requirementSetID = requirement_set.requirementSetID
        context.updatedAt = datetime.now()

    db.commit()
    db.refresh(context)

    validation = None
    if create_validation:
        # --- 6. Create Validation Entry ---
        now = datetime.utcnow()
        validation = DegreePlanValidation(
            adviseeID=advisee_id,
            contextID=context.contextID,
            requirementSetID=requirement_set.requirementSetID,
            status=ValidationStatus.RUNNING,
            runType=ValidationRunType.MANUAL,
            startedAt=now,
            createdAt=now,
            updatedAt=now,
        )
        db.add(validation)
        db.commit()
        db.refresh(validation)

        # Placeholder validation record for the import; actual validations run separately.
        validation.issues = []
        validation.status = ValidationStatus.PASSED
        validation.completionPercent = 100.0
        validation.finishedAt = datetime.now()

        db.commit()
        db.refresh(validation)

    return {
        "requirementSet": requirement_set,
        "context": context,
        "validation": validation,
    }
