# services/pdf_parser.py
import re
import json
from typing import Optional

from services.course_matching import extract_codes_from_text

COURSE_PATTERN = re.compile(r"([A-Z]{2,4}\s*\d{3,4})")
PREREQ_KEYWORDS = [
    ("PREREQUISITE OR CONCURRENT", "PREREQ_OR_CONCURRENT"),
    ("PRE- OR COREQUISITE", "PREREQ_OR_CONCURRENT"),
    ("PREREQ/COREQ", "PREREQ_OR_CONCURRENT"),
    ("PREREQ OR CONCURRENT", "PREREQ_OR_CONCURRENT"),
    ("COREQUISITE", "COREQUISITE"),
    ("CO-REQUISITE", "COREQUISITE"),
    ("PREREQUISITE", "PREREQUISITE"),
]
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


def _split_prereq_options(text: str, target_code: Optional[str]) -> list:
    segments = re.split(r"\bor\b", text, flags=re.IGNORECASE)
    options = []
    for segment in segments:
        codes = [
            code for code in sorted(extract_codes_from_text(segment))
            if code != target_code
        ]
        if codes:
            options.append(codes)
    if options:
        return options

    codes = [
        code for code in sorted(extract_codes_from_text(text))
        if code != target_code
    ]
    return [codes] if codes else []


def _extract_target_from_prefix(prefix: str) -> Optional[str]:
    codes = sorted(extract_codes_from_text(prefix))
    return codes[-1] if codes else None


def extract_prerequisites(text: str):
    """
    Parse prerequisite/corequisite statements from catalog text.
    Returns mapping { course_code: [ {type, options, text} ] }.
    """
    mapping: dict[str, list[dict]] = {}
    current_course: Optional[str] = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        upper = line.upper()

        matched = next((pair for pair in PREREQ_KEYWORDS if pair[0] in upper), None)
        line_codes = sorted(extract_codes_from_text(line))
        if matched:
            keyword, clause_type = matched
            idx = upper.find(keyword)
            prefix_text = raw_line[:idx] if idx >= 0 else raw_line
            suffix_text = raw_line[idx + len(keyword):] if idx >= 0 else raw_line

            target = _extract_target_from_prefix(prefix_text) or current_course
            if not target and line_codes:
                target = line_codes[0]

            remainder = suffix_text.split(":", 1)[-1]

            options = _split_prereq_options(remainder, target)
            if target and options:
                clauses = mapping.setdefault(target, [])
                clauses.append({
                    "type": clause_type,
                    "options": options,
                    "text": line,
                })
            continue

        if line_codes:
            current_course = line_codes[0]

    return mapping


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
