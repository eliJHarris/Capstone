# services/degree_importer.py
from datetime import datetime
from typing import Optional

import requests
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


def _build_requirement_groups(program_name: str, courses):
    required = sum(course.get("credits", 0) or 0 for course in courses)
    return [
        {
            "id": "auto-import",
            "title": program_name,
            "requiredCredits": required or 1,
            "description": "Auto-generated from degree audit import",
            "courses": courses,
        }
    ]


def import_degree_plan_from_pdf_url(db: Session, advisee_id: int, pdf_url: str):
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
    result = run_pdf_scraper(normalized, max_pages=3)
    if not result:
        raise Exception("No PDF found at provided URL")

    # Pick first PDF found
    pdf = list(result.values())[0]
    text = pdf["text"]

    # 2. PARSE PROGRAM INFO
    programName, catalogYear = extract_program_info(text)

    # 3. PARSE COMPLETED COURSES
    completed = _normalize_completed_courses(extract_courses(text))

    # 4. FIND OR CREATE REQUIREMENT SET
    requirement_set = (
        db.query(DegreeRequirementSet)
        .filter(
            DegreeRequirementSet.programName == programName,
            DegreeRequirementSet.catalogYear == catalogYear
        )
        .first()
    )

    if not requirement_set:
        now = datetime.utcnow()
        requirement_set = DegreeRequirementSet(
            programCode=programName.replace(" ", "-").upper(),
            catalogYear=catalogYear,
            programName=programName,
            totalCredits=120,
            requirementData=_build_requirement_groups(programName, completed),
            sourceDocument=normalized,
            createdAt=now,
            updatedAt=now,
        )
        db.add(requirement_set)
        db.commit()
        db.refresh(requirement_set)

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

    # Simulate validation result
    completed_codes = {c["code"] for c in completed}
    required_codes = {"ENG 1013", "MATH 2804", "CS 1013", "CS 2023"}  # example

    missing = list(required_codes - completed_codes)
    issues = []
    if missing:
        issues.append({
            "requirementId": "CORE",
            "message": "Missing required core courses",
            "missingCourses": missing
        })

    validation.issues = issues
    validation.status = ValidationStatus.PASSED if not issues else ValidationStatus.FAILED
    validation.completionPercent = (
        (len(required_codes) - len(missing)) / len(required_codes) * 100
    )
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

    # --- 3. Parse Completed Courses ---
    completed = _normalize_completed_courses(extract_courses(text))

    # --- 4. Find or Create Requirement Set ---
    requirement_set = (
        db.query(DegreeRequirementSet)
        .filter(
            DegreeRequirementSet.programName == programName,
            DegreeRequirementSet.catalogYear == catalogYear
        )
        .first()
    )

    if not requirement_set:
        now = datetime.utcnow()
        requirement_set = DegreeRequirementSet(
            programCode=programName.replace(" ", "-").upper(),
            catalogYear=catalogYear,
            programName=programName,
            totalCredits=120,
            requirementData=_build_requirement_groups(programName, completed),
            sourceDocument=source_label,
            createdAt=now,
            updatedAt=now,
        )
        db.add(requirement_set)
        db.commit()
        db.refresh(requirement_set)

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

    # Simulated course comparison (same as existing method)
    completed_codes = {c["code"] for c in completed}
    required_codes = {"ENG 1013", "MATH 2804", "CS 1013", "CS 2023"}

    missing = list(required_codes - completed_codes)
    issues = []

    if missing:
        issues.append({
            "requirementId": "CORE",
            "message": "Missing required core courses",
            "missingCourses": missing
        })

    validation.issues = issues
    validation.status = ValidationStatus.PASSED if not issues else ValidationStatus.FAILED
    validation.completionPercent = (
        (len(required_codes) - len(missing)) / len(required_codes) * 100
    )
    validation.finishedAt = datetime.now()

    db.commit()
    db.refresh(validation)

    return {
        "requirementSet": requirement_set,
        "context": context,
        "validation": validation,
    }
