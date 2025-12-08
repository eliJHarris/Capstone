"""
COMPLETE STRUCTURED DEGREE PLAN IMPORTER (CONCENTRATION-ENABLED VERSION)
------------------------------------------------------------------------
This importer produces FULLY VALIDATED requirement structures that the
degree validator + LLM can safely reason about.

Major additions:
- Automatic extraction of Concentrations from PDF text
- Support for required hours and choose hours
- Normalized course list construction
- Deep-copy protection against cross-student mutation
"""

import re
import copy
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from models.advisee import AdviseeProfile
from models.degree_plan import DegreeRequirementSet, ValidationRunType
from services.pdf_parser import extract_program_info


# --------------------------------------------
# 1. Regex for course codes (UAFS format)
# --------------------------------------------
COURSE_REGEX = re.compile(r"\b([A-Z]{2,4}\s?\d{3,4}[A-Z]?)\b")


def extract_course_codes(text: str) -> List[str]:
    """Extracts all unique course codes from PDF text."""
    matches = COURSE_REGEX.findall(text)
    return sorted({m.replace(" ", "").upper() for m in matches})


def extract_course_titles(text: str) -> Dict[str, str]:
    """
    Robust course title extractor for UAFS PDFs.
    Captures patterns such as:
      CS 1013 Intro to Programming
      MATH 2804 Calculus I
      STAT 2503 Probability & Statistics

    This version works even when:
      - There are no 'Hours' or 'Grade' markers
      - Titles wrap across lines
      - Titles contain punctuation
      - ACTS equivalency or prereq text follows the title

    Extraction stops when:
      - Newline is reached, OR
      - Another course code begins.
    """

    title_map: Dict[str, str] = {}

    # Pattern:
    #   CODE   TITLE   (stop at next code OR newline OR EOF)
    pattern = re.compile(
        r"\b([A-Z]{2,4}\s?\d{3,4}[A-Z]?)\b"          # Course code (e.g., CS 1013)
        r"\s+"                                      # Space(s)
        r"([A-Za-z][A-Za-z0-9&.,'()\-/\s]+?)"       # The course title
        r"(?=\n|$|\b[A-Z]{2,4}\s?\d{3,4}[A-Z]?\b)", # Lookahead = stop conditions
        re.MULTILINE,
    )

    for match in pattern.finditer(text):
        raw_code, raw_title = match.groups()

        code = _normalize_code(raw_code)
        title = raw_title.strip(" -–—\n\t")

        # Remove trailing parenthetical strings such as:
        #   (ACTS Equivalency ...)
        #   (Prerequisite: ...)
        title = re.sub(r"\([^)]*\)$", "", title).strip()

        # Remove trailing credit notations or weird artifacts
        title = re.sub(r"\b\d+\s*Hours?$", "", title).strip()

        if code and title:
            if code not in title_map:  # keep first occurrence
                title_map[code] = title

    return title_map



# --------------------------------------------
# 2. GEN ED CATEGORY DEFINITIONS
# --------------------------------------------
CATEGORY_RULES = {
    "english": {
        "title": "English Composition",
        "type": "category",
        "creditsRequired": 6,
        "courses": ["ENG1013", "ENG1023"],
    },
    "speech": {
        "title": "Speech / Communications",
        "type": "category",
        "creditsRequired": 3,
        "courses": ["SPCH1203"],
    },
    "fine_arts": {
        "title": "Fine Arts",
        "type": "category",
        "creditsRequired": 3,
        "courses": ["ART1103", "THEA1203", "MUSI2763"],
    },
    "humanities": {
        "title": "Humanities",
        "type": "category",
        "creditsRequired": 3,
        "courses": ["HUMN1403", "HUMN1503", "PHIL2753", "PHIL3203"],
    },
    "history_gov": {
        "title": "U.S. History / Government",
        "type": "choose_one",
        "options": ["HIST1163", "HIST1173", "HIST2753", "POLS2753"],
    },
}


# --------------------------------------------
# 3. LAB SCIENCE PAIRS
# --------------------------------------------
LAB_SCIENCE = {
    "title": "Lab Science Requirement",
    "type": "paired_group",
    "min": 1,
    "pairs": [
        {"lecture": "BIOL1153", "lab": "BIOL1151"},
        {"lecture": "CHEM1303", "lab": "CHEM1301"},
        {"lecture": "GEOL1253", "lab": "GEOL1251"},
    ],
}


# --------------------------------------------
# 4. DEFAULT CS CORE (kept unchanged)
# --------------------------------------------
CS_MAJOR_CORE = {
    "title": "Computer Science Major Core",
    "type": "credit_minimum",
    "creditsRequired": 42,
    "courses": [
        "CS1013", "CS1063", "CS2023", "CS3013",
        "CS3023", "CS3033", "CS3223", "CS3413", "CS3443",
        "STAT2503", "MATH2804",
        "CS4XX3"
    ],
}


# --------------------------------------------
# 5. ELECTIVE POOL BUILDER
# --------------------------------------------
def build_elective_pool(course_list: List[str], min_credits: int = 20) -> Dict:
    """Builds the elective pool requirement."""
    prepared = []
    for entry in course_list or []:
        if isinstance(entry, dict):
            prepared.append(entry)
        else:
            prepared.append({"code": entry, "title": entry, "credits": 3.0})

    prepared.sort(key=lambda x: _normalize_code(x.get("code") or ""))

    return {
        "title": "General Electives",
        "type": "elective_pool",
        "creditsRequired": min_credits,
        "courses": prepared,
    }


# --------------------------------------------
# 6. Normalization Utilities
# --------------------------------------------
def _normalize_code(value: Optional[str]) -> str:
    if not value:
        return ""
    return str(value).replace(" ", "").upper().strip()


def _extract_hours_from_text(text: str) -> Optional[int]:
    """
    Detect patterns like:
    "12 hours", "nine hours", "Required 12 hours", "Choose 9 hours"
    """
    text = text.lower()
    num_map = {
        "one": 1, "two": 2, "three": 3, "four": 4,
        "five": 5, "six": 6, "seven": 7, "eight": 8,
        "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    }

    # numeric first
    m = re.search(r"(\d+)\s+hours?", text)
    if m:
        return int(m.group(1))

    # number words
    for word, val in num_map.items():
        if f"{word} hour" in text:
            return val

    return None


def _normalize_course_entry(entry, default_credits: float = 3.0) -> Optional[Dict]:
    code = None
    title = None
    credits = default_credits

    if isinstance(entry, dict):
        code = entry.get("code")
        title = entry.get("title") or code
        credits = entry.get("credits") or default_credits
    else:
        code = entry
        title = entry

    normalized_code = _normalize_code(code)
    if not normalized_code:
        return None

    try:
        credits_value = float(credits)
    except:
        credits_value = default_credits

    if credits_value <= 0:
        credits_value = default_credits

    return {
        "code": normalized_code,
        "title": str(title) if title else normalized_code,
        "credits": credits_value,
    }


def _normalize_courses(courses):
    normalized = []
    for entry in courses or []:
        n = _normalize_course_entry(entry)
        if n:
            normalized.append(n)
    return normalized


def _normalize_group(group: Dict) -> Dict:
    normalized = copy.deepcopy(group)
    if "courses" in normalized:
        normalized["courses"] = _normalize_courses(normalized["courses"])
    for key in ("requiredCourses", "chooseCourses"):
        if key in normalized:
            normalized[key] = _normalize_courses(normalized[key])
    return normalized


def _apply_title_map_to_group(group: Dict, title_map: Dict[str, str]) -> Dict:
    """
    If a course entry is missing a title (or title == code),
    inject the title from the parsed PDF map when available.
    """
    def enrich_courses(course_list):
        enriched = []
        for entry in course_list or []:
            if isinstance(entry, dict):
                enriched_entry = copy.deepcopy(entry)
                code = _normalize_code(enriched_entry.get("code"))
                title = enriched_entry.get("title")
                if code and (not title or _normalize_code(title) == code):
                    mapped = title_map.get(code)
                    if mapped:
                        enriched_entry["title"] = mapped
                enriched.append(enriched_entry)
            else:
                code = _normalize_code(entry)
                enriched.append({
                    "code": code,
                    "title": title_map.get(code) or code,
                    "credits": 3.0,
                })
        return enriched

    updated = copy.deepcopy(group)
    if "courses" in updated:
        updated["courses"] = enrich_courses(updated.get("courses"))
    for key in ("requiredCourses", "chooseCourses"):
        if key in updated:
            updated[key] = enrich_courses(updated.get(key))
    return updated


# -------------------------------------------------------------
# 7. CONCENTRATION PARSING LOGIC
# -------------------------------------------------------------
CONC_TITLE_PATTERN = re.compile(
    r"(?P<title>.+?)\s*(?:concentration\s*)?(?:code[:\-]?)?\s*C0\d{2,3}",  # e.g., "Core Accounting Concepts C059" or "Concentration Code: C021"
    re.IGNORECASE
)

COURSE_LINE_PATTERN = re.compile(r"\b([A-Z]{2,4}\s?\d{3,4}[A-Z]?)\b")


def _extract_concentration_blocks(pdf_text: str, default_title: Optional[str] = None) -> List[Dict]:
    """
    Extracts a list of concentration requirement groups.
    Each group:
      {
        "title": "...",
        "hoursRequired": 12,
        "requiredCourses": [],
        "chooseCourses": []
      }
    """

    lines = pdf_text.split("\n")
    concentrations = []
    current = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        lower = line.lower()

        # Detect concentration title
        title = None
        if "concentration code" in lower:
            prefix = line.split("concentration code", 1)[0].strip(" :-")
            title = prefix or default_title
        if not title:
            mt = CONC_TITLE_PATTERN.search(line)
            if mt:
                title = mt.group("title").strip(" :-")

        if title:
            clean_title = re.sub(r"\bconcentration\s*code\b", "", title, flags=re.IGNORECASE).strip(" :-")
            clean_title = clean_title or default_title or "Concentration"
            if "concentration code" in lower or "concentration codes" in lower:
                # This is a header listing options, not a real concentration block
                continue
            # Save previous
            if current:
                concentrations.append(current)

            current = {
                "title": clean_title,
                "hoursRequired": None,
                "requiredCourses": [],
                "chooseCourses": [],
                "mode": None,   # "required" or "choose"
            }
            continue

        if not current:
            continue

        # Detect hours in this line
        hours = _extract_hours_from_text(line)
        if hours:
            current["hoursRequired"] = hours

        # Detect REQUIRED or CHOOSE mode
        if "requires" in lower or "required" in lower:
            current["mode"] = "required"
        if "choose" in lower:
            current["mode"] = "choose"

        # Detect course codes
        courses = COURSE_LINE_PATTERN.findall(line)
        if courses:
            mode = current["mode"] or "required"
            normalized = [_normalize_code(c) for c in courses]

            if mode == "required":
                current["requiredCourses"].extend(normalized)
            elif mode == "choose":
                current["chooseCourses"].extend(normalized)

    # Append last block
    if current:
        concentrations.append(current)

    return concentrations


def _convert_concentration_blocks_to_groups(blocks: List[Dict]):
    """
    Convert the extracted raw concentration blocks into requirement group objects.
    """

    groups = []

    for block in blocks:
        title = block["title"]
        hours = block["hoursRequired"] or 12  # fallback

        required_courses = [{"code": c, "credits": 3.0} for c in block["requiredCourses"]]
        choose_courses = [{"code": c, "credits": 3.0} for c in block["chooseCourses"]]
        all_courses = required_courses + choose_courses

        # If the detected hours look too low compared to listed courses, bump to a sensible default.
        if hours < 9 and required_courses:
            inferred_hours = min(12, len(required_courses) * 3)
            hours = max(hours, inferred_hours)

        group = {
            "id": title,
            "title": title,
            "type": "concentration",
            "hoursRequired": hours,
            "requiredCourses": required_courses,
            "chooseCourses": choose_courses,
            "courses": all_courses,
        }

        groups.append(group)

    return groups


# -------------------------------------------------------------
# 7b. MINOR PARSING LOGIC
# -------------------------------------------------------------
MINOR_TITLE_PATTERN = re.compile(
    r"(?P<title>.+?)\s*-?\s*Minor\s*Code\s*:\s*A\d{3}",  # e.g., "Anthropology-Minor Code: A022"
    re.IGNORECASE,
)


def _clean_minor_title(raw: str) -> str:
    title = (raw or "").strip()
    title = re.sub(r"\bminor\b", "", title, flags=re.IGNORECASE).strip(" :-")
    return title or "Minor"


def _extract_minor_blocks(pdf_text: str) -> List[Dict]:
    """
    Extract a list of minor requirement groups using the same pattern as concentrations.
    """
    lines = pdf_text.split("\n")
    minors = []
    current = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        lower = line.lower()

        # Detect minor title
        title = None
        if "minor code" in lower:
            title = line.split("minor code", 1)[0]
            if "-" in title:
                title = title.split("-")[-1]
        if not title:
            mt = MINOR_TITLE_PATTERN.search(line)
            if mt:
                title = mt.group("title")

        if title:
            clean_title = _clean_minor_title(title)
            if current:
                minors.append(current)
            current = {
                "title": clean_title,
                "hoursRequired": None,
                "requiredCourses": [],
                "chooseCourses": [],
                "mode": None,
            }
            continue

        if not current:
            continue

        hours = _extract_hours_from_text(line)
        if hours:
            current["hoursRequired"] = hours

        if "required" in lower:
            current["mode"] = "required"
        if "choose" in lower or "select" in lower:
            current["mode"] = "choose"

        courses = COURSE_LINE_PATTERN.findall(line)
        if courses:
            mode = current["mode"] or "required"
            normalized = [_normalize_code(c) for c in courses]
            target = "requiredCourses" if mode == "required" else "chooseCourses"
            current[target].extend(normalized)

    if current:
        minors.append(current)

    return minors


def _convert_minor_blocks_to_groups(blocks: List[Dict]) -> List[Dict]:
    groups = []

    for block in blocks:
        title = block["title"]
        hours = block["hoursRequired"] or 18

        required_courses = [
            _normalize_course_entry({"code": c, "credits": 3.0})
            for c in block.get("requiredCourses", [])
        ]
        choose_courses = [
            _normalize_course_entry({"code": c, "credits": 3.0})
            for c in block.get("chooseCourses", [])
        ]

        required_courses = [c for c in required_courses if c]
        choose_courses = [c for c in choose_courses if c]
        all_courses = required_courses + choose_courses

        group = {
            "id": f"minor:{title}",
            "title": f"Minor: {title}",
            "type": "minor",
            "hoursRequired": hours,
            "creditsRequired": hours,
            "requiredCourses": required_courses,
            "chooseCourses": choose_courses,
            "courses": all_courses,
        }
        groups.append(group)

    return groups


# -------------------------------------------------------------
# 8. IMPORTER PIPELINE
# -------------------------------------------------------------
def import_degree_plan_from_pdf_url(
    db: Session,
    advisee_id: int,
    pdf_url: str,
    required_keywords: Optional[List[str]] = None,
    create_validation: bool = True,
):
    """Full pipeline: read PDF → extract requirements → save."""

    from pdf_scraper.scrape_pdfs import scrape_pdf_text
    pdf_text = scrape_pdf_text(pdf_url)

    if not pdf_text:
        raise HTTPException(400, "Unable to read PDF content")

    # Optional PDF keyword validation
    if required_keywords:
        lower = pdf_text.lower()
        if not any(k.lower() in lower for k in required_keywords):
            raise HTTPException(400, "PDF does not match expected plan")

    program_hint, catalog_hint = extract_program_info(pdf_text)

    # Fetch profile early so we can tailor major requirements
    profile = db.query(AdviseeProfile).filter(AdviseeProfile.adviseeID == advisee_id).first()
    if not profile:
        raise HTTPException(404, "Advisee profile not found")

    program_code = (program_hint or profile.major or "AUTO").strip() or "AUTO"
    program_code = program_code.upper()

    # Extract all course codes from entire PDF
    found_codes = extract_course_codes(pdf_text)
    title_map = extract_course_titles(pdf_text)

    # ---------------------------------------------------------
    # Build base requirement groups (Gen Ed, Lab Science, etc.)
    # ---------------------------------------------------------
    requirement_groups = [
        _normalize_group(
            _apply_title_map_to_group(copy.deepcopy(rule), title_map)
        )
        for rule in CATEGORY_RULES.values()
    ]

    # Lab science
    requirement_groups.append(
        _normalize_group(
            _apply_title_map_to_group(copy.deepcopy(LAB_SCIENCE), title_map)
        )
    )

    # Major core fallback for CS programs to populate major bucket
    core_codes = {c.get("code") for g in requirement_groups for c in g.get("courses", []) if c.get("code")}
    if "CS" in program_code or "COMPUTER" in program_code:
        cs_core = _normalize_group(
            _apply_title_map_to_group(copy.deepcopy(CS_MAJOR_CORE), title_map)
        )
        requirement_groups.append(cs_core)
        core_codes.update({c.get("code") for c in cs_core.get("courses", []) if c.get("code")})

    # Elective pool
    elective_codes = sorted(c for c in found_codes if c not in core_codes)

    requirement_groups.append(
        _normalize_group(
            _apply_title_map_to_group(
                build_elective_pool([
                    {"code": c, "title": title_map.get(_normalize_code(c), c), "credits": 3.0}
                    for c in elective_codes
                ]),
                title_map,
            )
        )
    )

    # ---------------------------------------------------------
    # NEW: Concentration extraction
    # ---------------------------------------------------------
    concentration_blocks = _extract_concentration_blocks(pdf_text, default_title=program_hint)
    concentration_groups = _convert_concentration_blocks_to_groups(concentration_blocks)

    # Append concentration groups at BOTTOM
    for g in concentration_groups:
        requirement_groups.append(
            _normalize_group(_apply_title_map_to_group(copy.deepcopy(g), title_map))
        )

    # ---------------------------------------------------------
    # NEW: Minor extraction
    # ---------------------------------------------------------
    minor_blocks = _extract_minor_blocks(pdf_text)
    minor_groups = _convert_minor_blocks_to_groups(minor_blocks)
    for g in minor_groups:
        requirement_groups.append(
            _normalize_group(_apply_title_map_to_group(copy.deepcopy(g), title_map))
        )

    # Catalog year marking with ADV suffix
    suffix = f"ADV-{advisee_id}"
    catalog_year = f"{(catalog_hint or 'AUTO').strip()}::{suffix}"

    scope = f"advisee:{advisee_id}"

    # Check if overwritten
    requirement = (
        db.query(DegreeRequirementSet)
        .filter(DegreeRequirementSet.sourceDocument == scope)
        .first()
    )

    if requirement:
        requirement.programCode = program_code
        requirement.catalogYear = catalog_year
        requirement.programName = profile.degree_plan or program_code
        requirement.totalCredits = 120
        requirement.requirementData = requirement_groups
    else:
        requirement = DegreeRequirementSet(
            programCode=program_code,
            catalogYear=catalog_year,
            programName=profile.degree_plan or program_code,
            totalCredits=120,
            requirementData=requirement_groups,
            sourceDocument=scope,
        )
        db.add(requirement)

    db.commit()
    db.refresh(requirement)

    # ---------------------------------------------------------
    # Attach degree plan context
    # ---------------------------------------------------------
    from models.degree_plan import AdviseeDegreeContext

    context = (
        db.query(AdviseeDegreeContext)
        .filter(AdviseeDegreeContext.adviseeID == advisee_id)
        .first()
    )

    if context:
        context.requirementSetID = requirement.requirementSetID
        context.notes = f"Imported from PDF: {pdf_url}"
    else:
        context = AdviseeDegreeContext(
            adviseeID=advisee_id,
            requirementSetID=requirement.requirementSetID,
            completedCourses=[],
            notes=f"Imported from PDF: {pdf_url}",
        )
        db.add(context)

    db.commit()

    # ---------------------------------------------------------
    # Trigger validation job
    # ---------------------------------------------------------
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
