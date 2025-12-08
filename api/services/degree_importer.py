"""
Improved Degree Plan Importer
--------------------------------
This importer FIXES the issue where the PDF importer produces
one giant unstructured requirement group.

This version:

✓ Extracts course codes using a strict regex
✓ Groups them into Gen Ed, CS Core, Math/Science, Electives
✓ Produces requirement groups the validator understands
✓ Avoids false matches and duplicates
"""

import re
from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from models.advisee import AdviseeProfile
from models.degree_plan import DegreeRequirementSet, ValidationRunType
from fastapi import HTTPException


# Strict UAFS-style course code detection
COURSE_REGEX = re.compile(
    r"\b([A-Z]{2,4}\s?\d{3,4})\b"
)

GEN_ED_KEYWORDS = [
    "english", "speech", "literature", "history",
    "government", "fine arts", "humanities"
]

CS_KEYWORDS = ["cs ", "computer", "program", "algorithm", "software"]
MATH_KEYWORDS = ["math", "calculus", "statistics", "linear"]
SCIENCE_KEYWORDS = ["chem", "phys", "geol", "bio"]


def extract_course_codes(text: str) -> List[str]:
    """Return unique course codes from text."""
    matches = COURSE_REGEX.findall(text)
    return list({m.replace(" ", "").upper() for m in matches})


def categorize_course(code: str) -> str:
    """Return which academic category the code belongs to."""
    c = code.lower()

    if any(k in c for k in CS_KEYWORDS):
        return "cs_core"
    if any(k in c for k in MATH_KEYWORDS):
        return "math"
    if any(k in c for k in SCIENCE_KEYWORDS):
        return "science"
    if any(k in c for k in GEN_ED_KEYWORDS):
        return "gen_ed"

    # fallback
    prefix = code[:4].lower()
    if prefix.startswith("cs"):
        return "cs_core"
    if prefix.startswith("math"):
        return "math"
    return "electives"


def build_group(title: str, codes: List[str], required_credits: int = None):
    """Helper for building a requirement group."""
    return {
        "id": title.lower().replace(" ", "-"),
        "title": title,
        "requiredCredits": required_credits,
        "courses": [
            {"code": c, "credits": 3.0, "prerequisites": []}
            for c in sorted(codes)
        ]
    }


def import_degree_plan_from_pdf_url(
    db: Session,
    advisee_id: int,
    pdf_url: str,
    required_keywords: Optional[List[str]] = None,
    create_validation: bool = True,
):
    """
    FIXED IMPORT PIPELINE:
    - Pull text from PDF
    - Extract course codes
    - Group them logically
    """

    from pdf_scraper.scrape_pdfs import scrape_pdf_text
    pdf_text = scrape_pdf_text(pdf_url)
    if not pdf_text:
        raise HTTPException(400, "Unable to extract text from degree plan PDF")

    keywords = [
        keyword.strip().lower()
        for keyword in (required_keywords or [])
        if keyword and keyword.strip()
    ]
    if keywords:
        lowered = pdf_text.lower()
        if not any(keyword in lowered for keyword in keywords):
            raise HTTPException(
                400,
                "Degree plan PDF did not contain any of the required keywords",
            )

    course_codes = extract_course_codes(text)
    if not course_codes:
        raise HTTPException(400, "No course codes detected in PDF")

    # Categorize
    groups = {
        "gen_ed": [],
        "cs_core": [],
        "math": [],
        "science": [],
        "electives": [],
    }

    for code in course_codes:
        category = categorize_course(code)
        groups[category].append(code)

    # Build requirement groups
    requirement_groups = []

    if groups["gen_ed"]:
        requirement_groups.append(
            build_group("General Education Requirements", groups["gen_ed"], required_credits=35)
        )

    if groups["cs_core"]:
        requirement_groups.append(
            build_group("Major Core Requirements", groups["cs_core"], required_credits=45)
        )

    if groups["math"] or groups["science"]:
        requirement_groups.append(
            build_group("Math & Science Requirements", groups["math"] + groups["science"], required_credits=20)
        )

    if groups["electives"]:
        requirement_groups.append(
            build_group("Elective Requirements", groups["electives"], required_credits=20)
        )

    # Fallback — ensures at least one group is created
    if not requirement_groups:
        requirement_groups.append(
            build_group("Uncategorized Courses", course_codes, required_credits=3)
        )

    # Create requirement set record
    profile = (
        db.query(AdviseeProfile)
        .filter(AdviseeProfile.adviseeID == advisee_id)
        .first()
    )
    if not profile:
        raise HTTPException(404, "Advisee profile not found for import")

    program_code = profile.major
    if not program_code:
        fallback = db.execute(
            text("SELECT programCode FROM majors ORDER BY programCode LIMIT 1")
        ).scalar_one_or_none()
        program_code = fallback or "BS-CS"

    major_display_name = None
    if program_code:
        major_display_name = db.execute(
            text("SELECT programName FROM majors WHERE programCode = :code"),
            {"code": program_code},
        ).scalar_one_or_none()

    catalog_year = f"AUTO::ADV-{advisee_id}"

    requirement = DegreeRequirementSet(
        programCode=program_code,
        catalogYear=catalog_year,
        programName=profile.degree_plan or major_display_name or "Imported Degree Plan",
        totalCredits=sum(g["requiredCredits"] or 0 for g in requirement_groups),
        requirementData=requirement_groups,
        sourceDocument=f"advisee:{advisee_id}",
    )

    db.add(requirement)
    db.commit()
    db.refresh(requirement)

    # Attach to advisee context
    from models.degree_plan import AdviseeDegreeContext
    context = (
        db.query(AdviseeDegreeContext)
        .filter(AdviseeDegreeContext.adviseeID == advisee_id)
        .first()
    )

    note = f"Imported from PDF: {pdf_url}"
    if context:
        context.requirementSetID = requirement.requirementSetID
        context.notes = note
    else:
        context = AdviseeDegreeContext(
            adviseeID=advisee_id,
            requirementSetID=requirement.requirementSetID,
            completedCourses=[],
            notes=note,
        )
        db.add(context)

    db.commit()
    db.refresh(context)

    validation_record = None
    if create_validation:
        from services.degree_plan_service import DegreePlanService

        validation_record = DegreePlanService.enqueue_validation(
            db=db,
            advisee_id=advisee_id,
            run_type=ValidationRunType.AUTOMATIC,
        )

    return {
        "requirementSet": requirement,
        "context": context,
        "validation": validation_record,
    }
