# services/pdf_parser.py
import re
import json

COURSE_PATTERN = re.compile(r"([A-Z]{2,4}\s*\d{3,4})")
PLANNED_KEYWORDS = {
    "NEED",
    "NEEDED",
    "REMAIN",
    "REMAINING",
    "STILL REQUIRED",
    "STILL NEEDED",
    "NOT COMPLETED",
    "NOT MET",
    "NOT SATISFIED",
    "UNMET",
    "TAKE",
    "REGISTER",
}
IN_PROGRESS_KEYWORDS = {
    "IN PROGRESS",
    "IN-PROGRESS",
    "INPROGRESS",
    "CURRENTLY ENROLLED",
    "CURRENT",
    "IP",
}
COMPLETED_KEYWORDS = {
    "COMPLETE",
    "COMPLETED",
    "FULFILLED",
    "EARNED",
    "PASSED",
    "SATISFIED",
    "TRANSFER",
    "APPROVED",
}
STATUS_PRIORITY = {
    "PLANNED": 0,
    "IN_PROGRESS": 1,
    "COMPLETED": 2,
}

PROGRAM_PATTERN = re.compile(r"(BS|BA|BBA|BFA|BE|BAS|BSED|BSCS|BS\-CS|BSCS)\s*[- ]?\s*([A-Za-z ]+)")
CATALOG_PATTERN = re.compile(r"(20\d{2})[\-–](20\d{2})")


def _infer_status_from_line(line: str) -> str:
    upper = line.upper()
    if any(keyword in upper for keyword in PLANNED_KEYWORDS):
        return "PLANNED"
    if any(keyword in upper for keyword in IN_PROGRESS_KEYWORDS):
        return "IN_PROGRESS"
    if any(keyword in upper for keyword in COMPLETED_KEYWORDS):
        return "COMPLETED"
    return "COMPLETED"


def extract_courses(text: str):
    """Return list: [{ code, title?, credits?, status }] from PDF text"""
    lines = text.splitlines()
    unique = {}

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        status = _infer_status_from_line(stripped)
        matches = COURSE_PATTERN.findall(stripped.upper())
        if not matches:
            continue
        for m in matches:
            c = m.replace(" ", "").upper()
            code = f"{c[:-4]} {c[-4:]}"
            record = unique.get(code)
            if record is None or STATUS_PRIORITY[status] >= STATUS_PRIORITY[record["status"]]:
                unique[code] = {
                    "code": code,
                    "title": None,
                    "credits": None,
                    "status": status,
                }

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
