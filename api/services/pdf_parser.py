# services/pdf_parser.py
import re
import json

COURSE_PATTERN = re.compile(r"([A-Z]{2,4}\s*\d{3,4})")

PROGRAM_PATTERN = re.compile(r"(BS|BA|BBA|BFA|BE|BAS|BSED|BSCS|BS\-CS|BSCS)\s*[- ]?\s*([A-Za-z ]+)")
CATALOG_PATTERN = re.compile(r"(20\d{2})[\-–](20\d{2})")


def extract_courses(text: str):
    """Return list: [{ code, title?, credits? }] from PDF text"""
    matches = COURSE_PATTERN.findall(text)
    courses = []

    for m in matches:
        c = m.replace(" ", "").upper()
        code = f"{c[:-4]} {c[-4:]}"
        courses.append({"code": code, "title": None, "credits": None})

    # Dedupe
    unique = {c["code"]: c for c in courses}
    return list(unique.values())


def extract_program_info(text: str):
    """Detect program name and catalog year from degree audit PDF"""
    program = "Unknown Program"
    catalog = "Unknown"

    prog_match = PROGRAM_PATTERN.search(text)
    if prog_match:
        program = prog_match.group(0).strip()

    cat_match = CATALOG_PATTERN.search(text)
    if cat_match:
        catalog = f"{cat_match.group(1)}-{cat_match.group(2)}"

    return program, catalog
