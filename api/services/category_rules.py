# category_rules.py
import re
from typing import Optional

# Category rule definitions
CATEGORY_RULES = {
    "lab_science": {
        "label": "Lab Science Requirement",
        "group_keywords": {
            "LAB SCIENCE", "SCIENCE LAB", "LABORATORY SCIENCE",
            "SCIENCE W/LAB", "SCIENCE W-LAB", "NATURAL SCIENCE",
            "SCIENCE LECTURE/LAB", "LAB-BASED SCIENCE",
        },
        "course_prefixes": {
            "ASTR", "BIOL", "CHEM", "GEOG", "GEOL", "GEOS", "PHSC", "PHYS",
        },
        "course_keywords": {
            "BIOLOGY", "CHEMISTRY", "PHYSICS",
            "GEOLOGY", "ASTRONOMY", "LAB",
        },
    },

    "fine_arts": {
        "label": "Fine Arts Requirement",
        "group_keywords": {
            "FINE ART", "FINE ARTS", "ARTS REQUIREMENT",
            "CREATIVE ARTS", "ART/MUSIC", "ART OR MUSIC",
            "ART OR THEATRE",
        },
        "course_prefixes": {"ART", "ARTH", "DANC", "FILM", "MUS", "THEA"},
        "course_keywords": {
            "FINE ART", "MUSIC", "THEATRE", "THEATER",
            "DANCE", "ART HISTORY", "ART APPRECIATION",
        },
    },

    "concentration": {
        "label": "Concentration Requirement",
        "group_keywords": {
            "CONCENTRATION", "CHOOSE A CONCENTRATION",
            "AREA OF CONCENTRATION", "AREA OF EMPHASIS",
            "MAJOR CONCENTRATION", "SPECIALIZATION",
            # Now includes track-style naming
            "TRACK", "OPTION", "PATHWAY",
        },
        "course_prefixes": set(),
        "course_keywords": {
            "CONCENTRATION", "SPECIALIZATION", "EMPHASIS", "TRACK",
        },
    },
}

COURSE_CODE_PATTERN = re.compile(r"\b([A-Z]{2,4})\s*-?\s*(\d{3,4}[A-Z]?)\b")


def extract_codes(text: str):
    if not text:
        return set()
    matches = COURSE_CODE_PATTERN.findall(text.upper())
    return {f"{prefix} {num}" for prefix, num in matches}


def detect_category_from_group(title: str, description: str):
    full_text = f"{title or ''} {description or ''}".upper()

    for category, rule in CATEGORY_RULES.items():
        if any(keyword in full_text for keyword in rule["group_keywords"]):
            return category

    return None


def detect_category_from_courses(courses: list, group_category: Optional[str] = None):
    """
    Secondary detection: inspects course titles/codes when the group itself did not contain category keywords.
    """
    candidate_categories = (
        [group_category] if group_category else list(CATEGORY_RULES.keys())
    )

    for category in candidate_categories:
        rule = CATEGORY_RULES.get(category)
        if not rule:
            continue

        prefixes = rule["course_prefixes"]
        keywords = rule["course_keywords"]

        for course in courses:
            title = (course.get("title") or "").upper()
            code = (course.get("code") or "").upper()

            if any(code.startswith(prefix) for prefix in prefixes):
                return category

            combined = f"{title} {code}"
            if any(kw in combined for kw in keywords):
                return category

    return None


def completed_satisfies_category(category: str, completed_courses: list):
    """
    Returns True if ANY completed course satisfies the category.
    """
    rule = CATEGORY_RULES.get(category)
    if not rule:
        return False

    prefixes = rule["course_prefixes"]
    keywords = rule["course_keywords"]

    for course in completed_courses:
        code = (course.get("code") or "").upper()
        title = (course.get("title") or "").upper()

        if any(code.startswith(prefix) for prefix in prefixes):
            return True

        combined = f"{title} {code}"
        if any(kw in combined for kw in keywords):
            return True

    return False
