# course_matching.py
import re
from typing import List, Optional, Set, Tuple

COURSE_CODE_PATTERN = re.compile(r"\b([A-Z]{2,4})\s*-?\s*(\d{3,4}[A-Z]?)\b")

COMPLETED_STATUSES = {
    "COMPLETED",
    "TRANSFER",
    "APPROVED",
    "WAIVED",
    "SATISFIED",
    "PASS",
}


def extract_codes_from_text(value: Optional[str]) -> Set[str]:
    if not value:
        return set()
    text = value.upper()
    matches = set()

    for match in COURSE_CODE_PATTERN.finditer(text):
        prefix, number = match.groups()
        if not prefix or not number:
            continue

        if prefix in {"OF", "ACT"}:
            continue

        matches.add(f"{prefix} {number}")

    return matches


def expand_requirement_codes(course: dict, group_description: Optional[str]) -> Set[str]:
    """
    Expand requirement course to all potential course-code matches.
    """
    codes = set()
    codes |= extract_codes_from_text(course.get("code"))
    codes |= extract_codes_from_text(course.get("title"))
    codes |= extract_codes_from_text(course.get("description"))

    if not codes and group_description:
        codes |= extract_codes_from_text(group_description)

    return codes


def normalize_text(*items: Optional[str]) -> str:
    parts = [i.strip().upper() for i in items if isinstance(i, str) and i.strip()]
    return " ".join(parts) if parts else ""


def serialize_courses(courses: List[dict]) -> List[dict]:
    """
    Standardizes completed-course objects into a consistent shape.
    """
    result = []
    for c in courses:
        result.append({
            "code": (c.get("code") or "").upper().strip(),
            "title": c.get("title"),
            "credits": float(c.get("credits") or 0),
            "term": c.get("term"),
            "status": (c.get("status") or "COMPLETED").upper(),
        })
    return result


def merge_completed_sources(*sources: Optional[List[dict]]) -> List[dict]:
    """
    Merge transcript and schedule completed courses, dedupe, and standardize.
    """
    merged: List[dict] = []
    seen: Set[Tuple[str, str, str]] = set()

    for source in sources:
        for c in source or []:
            if not isinstance(c, dict):
                continue

            code = (c.get("code") or "").upper().strip()
            term = (c.get("term") or "").upper().strip()
            title = (c.get("title") or "").upper().strip()
            status = (c.get("status") or "").upper().strip()
            source_label = (c.get("source") or "").upper().strip()

            if source_label == "PDF_IMPORT":
                continue
            if status not in COMPLETED_STATUSES:
                continue

            key = (code, term, title)
            if key in seen:
                continue

            seen.add(key)
            merged.append(c)

    return serialize_courses(merged)
