import logging
import math
import os
import re
from datetime import datetime
from typing import List, Optional, Set, Union
from urllib.parse import quote_plus

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import case
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from db.database import SessionLocal
from models.advisee import AdviseeProfile
from models.degree_plan import (
    AdviseeDegreeContext,
    DegreePlanValidation,
    DegreeRequirementSet,
    ValidationRunType,
    ValidationStatus,
)
from models.schedule import (
    Schedule,
    Class,
    Section,
    Course,
    ScheduleStatusEnum,
)
from schemas.degree_plan import (
    AdviseeContextUpsert,
    DegreeRequirementSetCreate,
    DegreeRequirementSetResponse,
)
from services.category_rules import (
    CATEGORY_RULES,
    detect_category_from_group,
    detect_category_from_courses,
    completed_satisfies_category,
)
from services.course_matching import (
    extract_codes_from_text,
    expand_requirement_codes,
    merge_completed_sources,
    serialize_courses,
)
from services.degree_importer import import_degree_plan_from_pdf_url
from services.degree_plan.llm_course_breakdown import classify_course_breakdown
from services.transcript_service import TranscriptService


CATALOG_SEARCH_URL = os.environ.get(
    "DEGREE_PLAN_CATALOG_SEARCH_URL",
    "https://uafs.edu/search?q={query}",
)
DEFAULT_CATALOG_YEAR = os.environ.get("DEGREE_PLAN_DEFAULT_CATALOG_YEAR", "2024-2025")

CATALOG_YEAR_PATTERN = re.compile(r"(20\d{2})(?:[-/](20\d{2}))?")


# ------------------------------
# UTILITIES
# ------------------------------

def normalize_catalog_display(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    marker = "::ADV-"
    return value.split(marker, 1)[0].strip() if marker in value else value


def _normalize_catalog_year_display(value: Optional[str]) -> Optional[str]:
    """
    Backwards-compatible alias used in existing unit tests.
    """
    return normalize_catalog_display(value)


def _merge_completed_course_sources(*sources: Optional[List[dict]]):
    """
    Backwards-compatible alias that points to the shared merge helper.
    """
    return merge_completed_sources(*sources)


def load_context(db: Session, advisee_id: int) -> Optional[AdviseeDegreeContext]:
    return (
        db.query(AdviseeDegreeContext)
        .filter(AdviseeDegreeContext.adviseeID == advisee_id)
        .first()
    )


# ------------------------------
# DEGREE PLAN SERVICE
# ------------------------------

class DegreePlanService:

    @staticmethod
    def _safe_float(value: Optional[Union[str, float, int]], default: Optional[float] = None) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(value: Optional[Union[str, float, int]], default: int = 0) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    # ----------------------------------------
    # CONTEXT LOADING & BOOTSTRAP
    # ----------------------------------------
    @staticmethod
    def _normalize_validation_record(record: Optional[DegreePlanValidation]):
        if record:
            record.issues = record.issues or []
            DegreePlanService._separate_issue_severity(record)
            if record.completionPercent is None:
                record.completionPercent = 0.0
            DegreePlanService._attach_concentration_summary(record)
            DegreePlanService._attach_concentration_metrics(record)
            DegreePlanService._attach_minor_metrics(record)
            DegreePlanService._attach_general_education_summary(record)
            DegreePlanService._attach_general_education_metrics(record)
            DegreePlanService._ensure_major_metrics(record)
        return record

    @staticmethod
    def _separate_issue_severity(record: DegreePlanValidation):
        entries = getattr(record, "issues", []) or []
        normalized = []
        warnings = []
        for entry in entries:
            container = entry
            severity = "ERROR"
            if isinstance(entry, dict):
                severity = str(entry.get("severity") or "ERROR").upper()
            else:
                severity = str(getattr(entry, "severity", "ERROR") or "ERROR").upper()

            if severity == "WARNING":
                warnings.append(entry)
            else:
                normalized.append(entry)

        record.issues = normalized
        record.warnings = warnings

    @staticmethod
    def _is_manual_requirement(requirement: Optional[DegreeRequirementSet], advisee_id: int) -> bool:
        if not requirement:
            return False
        scope = f"advisee:{advisee_id}"
        suffix = f"::ADV-{advisee_id}"
        source = (requirement.sourceDocument or "").strip()
        catalog = (requirement.catalogYear or "").strip()
        return bool(source == scope or catalog.endswith(suffix))

    @classmethod
    def _load_manual_requirement(cls, db: Session, advisee_id: int) -> Optional[DegreeRequirementSet]:
        scope = f"advisee:{advisee_id}"
        suffix = f"::ADV-{advisee_id}"
        requirement = (
            db.query(DegreeRequirementSet)
            .filter(DegreeRequirementSet.sourceDocument == scope)
            .order_by(DegreeRequirementSet.updatedAt.desc())
            .first()
        )
        if requirement:
            return requirement
        return (
            db.query(DegreeRequirementSet)
            .filter(DegreeRequirementSet.catalogYear.ilike(f"%{suffix}"))
            .order_by(DegreeRequirementSet.updatedAt.desc())
            .first()
        )

    @staticmethod
    def _is_corequisite_clause(clause_type: Optional[str]) -> bool:
        if not clause_type:
            return False
        normalized = str(clause_type).upper()
        compact = re.sub(r"[^A-Z]", "", normalized)
        return (
            "COREQ" in normalized
            or "CONCURRENT" in normalized
            or "COREQ" in compact
            or "CONCURRENT" in compact
        )

    @staticmethod
    def _is_zero_level_course_code(code: Optional[str]) -> bool:
        if not code:
            return False
        normalized = re.sub(r"\s+", "", str(code).upper())
        match = re.search(r"(\d+)", normalized)
        if not match:
            return False
        digits = match.group(1)
        return digits.startswith("0")

    
    COREQ_KEYS = {
        "co_requisites_if_placement_not_met",
        "corequisites",
        "corequisite",
        "co_reqs",
        "co-reqs",
        "co_req",
        "co-req",
        "coreq",
        "coreqs",
    }

    CONCENTRATION_CONTAINER_KEYS = (
        "concentrations",
        "concentrationOptions",
        "concentration_groups",
        "concentrationTracks",
        "tracks",
    )

    CONCENTRATION_SELECTION_KEYS = (
        "activeConcentrations",
        "selectedConcentrations",
        "studentConcentrations",
    )
    FOCUS_AREA_MINOR_KEYWORDS = (
        "MINOR",
        "MINOR REQUIREMENT",
        "MINOR REQUIREMENTS",
        "MINOR OPTION",
        "MINOR OPTIONS",
    )
    FOCUS_AREA_CONCENTRATION_KEYWORDS = (
        "CONCENTRATION",
        "CONCENTRATIONS",
        "EMPHASIS",
        "SPECIALIZATION",
        "SPECIALIZATION OPTION",
        "TRACK",
        "TRACKS",
        "FOCUS AREA",
        "AREA OF EMPHASIS",
        "AREA OF CONCENTRATION",
        "FOCUS OPTION",
        "PROGRAM OPTION",
    )

    GENERAL_ED_KEYWORDS = (
        "GENERAL EDUCATION",
        "GEN ED",
        "STATE GENERAL EDUCATION",
        "UAFS GENERAL EDUCATION",
    )

    GENERAL_ED_NUMBER_WORDS = {
        "ONE": 1,
        "TWO": 2,
        "THREE": 3,
        "FOUR": 4,
        "FIVE": 5,
        "SIX": 6,
        "SEVEN": 7,
        "EIGHT": 8,
        "NINE": 9,
        "TEN": 10,
        "ELEVEN": 11,
        "TWELVE": 12,
    }

    GENERAL_ED_SELECTION_PATTERN = re.compile(
        r"(?:SELECT|CHOOSE)\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|\d+)",
        re.IGNORECASE,
    )

    @staticmethod
    def _collect_assumed_corequisites(requirement_data):
        collected = set()

        def _walk(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    normalized_key = key.lower().replace("-", "_").replace(" ", "_")

                    # FIXED CLASS REFERENCE
                    if normalized_key in {k.lower() for k in DegreePlanService.COREQ_KEYS}:
                        if isinstance(value, dict):
                            for entries in value.values():
                                if isinstance(entries, (list, tuple)):
                                    for course in entries:
                                        cn = (course or "").upper().strip()
                                        if cn:
                                            collected.add(cn)

                    _walk(value)

            elif isinstance(node, (list, tuple)):
                for item in node:
                    _walk(item)

        _walk(requirement_data)
        return collected


    @staticmethod
    def _collect_zero_level_courses(requirement_data):
        collected = set()
        if not requirement_data:
            return collected

        for group in requirement_data:
            courses = group.get("courses") if isinstance(group, dict) else None
            if not courses:
                continue
            for course in courses:
                course_dict = course if isinstance(course, dict) else {}
                normalized = (course_dict.get("code") or "").upper().strip()
                if normalized and DegreePlanService._is_zero_level_course_code(normalized):
                    collected.add(normalized)

        return collected


    @classmethod
    def _detect_focus_area_type(cls, group: dict) -> str:
        text = " ".join([
            str(group.get("title") or ""),
            str(group.get("id") or ""),
            str(group.get("category") or ""),
        ]).upper()
        for keyword in cls.FOCUS_AREA_MINOR_KEYWORDS:
            if keyword in text:
                return "MINOR"
        return "CONCENTRATION"


    @classmethod
    def _determine_requirement_scope(cls, group: dict) -> str:
        text = " ".join([
            str(group.get("title") or ""),
            str(group.get("id") or ""),
            str(group.get("category") or ""),
        ]).upper()

        for keyword in cls.FOCUS_AREA_MINOR_KEYWORDS:
            if keyword in text:
                return "MINOR"

        for keyword in cls.FOCUS_AREA_CONCENTRATION_KEYWORDS:
            if keyword in text:
                return "CONCENTRATION"

        return "MAJOR"


    @classmethod
    def _is_general_education_group(cls, group: dict) -> bool:
        if not isinstance(group, dict):
            return False
        title = (group.get("title") or "").upper()
        description = (group.get("description") or "").upper()
        combined = f"{title} {description}".strip()
        if not combined:
            return False
        return any(keyword in combined for keyword in cls.GENERAL_ED_KEYWORDS)

    @classmethod
    def _infer_general_education_selection_count(cls, group: dict, courses: List[dict]) -> int:
        candidate_keys = (
            "requiredSelections",
            "requiredCount",
            "requiredCourses",
            "minimumSelections",
            "minSelections",
            "neededSelections",
            "selectionsRequired",
        )
        for key in candidate_keys:
            value = cls._safe_int(group.get(key))
            if value:
                return max(1, value)

        required_credits = cls._safe_float(
            group.get("requiredCredits")
            or group.get("requiredHours")
            or group.get("hoursNeeded"),
            0.0,
        )
        if required_credits and courses:
            total = 0.0
            for course in courses:
                credit_value = cls._safe_float(course.get("credits"), 0.0) or 0.0
                if credit_value <= 0:
                    credit_value = 3.0
                total += credit_value
            avg_credit = total / len(courses) if courses else 0
            if avg_credit <= 0:
                avg_credit = 3.0
            inferred = math.ceil(required_credits / avg_credit)
            if inferred > 0:
                return inferred

        text = f"{group.get('title') or ''} {group.get('description') or ''}"
        match = cls.GENERAL_ED_SELECTION_PATTERN.search(text or "")
        if match:
            token = match.group(1) or ""
            normalized = token.strip().upper()
            if normalized.isdigit():
                value = cls._safe_int(normalized)
                if value:
                    return max(1, value)
            mapped = cls.GENERAL_ED_NUMBER_WORDS.get(normalized)
            if mapped:
                return mapped

        # Fallback: require at least one selection, defaulting to two when options exist.
        if courses:
            return max(1, min(len(courses), 2))
        return 1

    @classmethod
    def _normalize_general_ed_course_label(cls, course: dict) -> str:
        code = (course.get("code") or "").strip()
        title = (course.get("title") or course.get("name") or "").strip()
        if code and title:
            return f"{code} - {title}".strip()
        return title or code or "Course Option"

    @classmethod
    def _handle_general_education_group(cls, group: dict, completed_codes: Set[str]):
        if not isinstance(group, dict):
            return None
        if not cls._is_general_education_group(group):
            return None

        raw_courses = group.get("courses") or []
        if not raw_courses:
            return None

        normalized_courses = []
        for entry in raw_courses:
            course = entry if isinstance(entry, dict) else {}
            code = (course.get("code") or "").upper().strip()
            label = cls._normalize_general_ed_course_label(course)
            normalized_courses.append({
                "code": code,
                "label": label,
                "credits": cls._safe_float(course.get("credits"), None),
            })

        required_count = cls._infer_general_education_selection_count(group, normalized_courses)
        taken_labels = []
        taken_codes = set()
        remaining_labels = []

        for course in normalized_courses:
            code = course["code"]
            label = course["label"]
            if code and code in completed_codes and code not in taken_codes:
                taken_codes.add(code)
                taken_labels.append(label)
            else:
                remaining_labels.append(label)

        satisfied_slots = min(required_count, len(taken_codes))
        remaining_slots = max(0, required_count - satisfied_slots)

        summary_entry = {
            "groupId": group.get("id") or group.get("title"),
            "title": group.get("title") or "General Education Requirement",
            "description": group.get("description"),
            "requiredSelections": required_count,
            "satisfiedSelections": satisfied_slots,
            "remainingSelections": remaining_slots,
            "takenCourses": taken_labels,
            "remainingCourses": remaining_labels,
        }

        return summary_entry, required_count, satisfied_slots

    @classmethod
    def _build_general_education_summary(cls, groups: List[dict], completed_codes: Set[str]):
        summary = []
        required_total = 0
        satisfied_total = 0
        for group in groups or []:
            result = cls._handle_general_education_group(group, completed_codes)
            if not result:
                continue
            entry, required, satisfied = result
            summary.append(entry)
            required_total += required
            satisfied_total += satisfied
        return summary, required_total, satisfied_total


    @staticmethod
    def _is_general_program_note(title: Optional[str], description: Optional[str]) -> bool:
        text = f"{title or ''} {description or ''}".strip().upper()
        if not text:
            return False
        return "STUDENT DEGREE PROGRAM REQUIREMENTS" in text


    @staticmethod
    def _build_completed_course_credit_map(courses: Optional[List[dict]]):
        credits = {}
        for course in courses or []:
            if not isinstance(course, dict):
                continue
            code = (course.get("code") or "").upper().strip()
            if not code:
                continue
            credit_value = DegreePlanService._safe_float(course.get("credits"), 0) or 0.0
            if credit_value <= 0:
                credit_value = 3.0
            if credit_value > credits.get(code, 0.0):
                credits[code] = credit_value
        return credits

    @classmethod
    def _collect_active_concentration_names(cls, group: dict) -> Set[str]:
        names = set()
        for key in cls.CONCENTRATION_SELECTION_KEYS:
            values = group.get(key)
            if isinstance(values, (list, tuple, set)):
                for value in values:
                    if isinstance(value, str) and value.strip():
                        names.add(value.strip().upper())
            elif isinstance(values, str) and values.strip():
                names.add(values.strip().upper())
        return names

    @staticmethod
    def _normalize_concentration_course_options(options) -> List[dict]:
        normalized = []
        for entry in options or []:
            if isinstance(entry, dict):
                label = (
                    entry.get("title")
                    or entry.get("label")
                    or entry.get("name")
                    or entry.get("code")
                    or entry.get("value")
                )
                code = entry.get("code") or entry.get("course") or entry.get("value")
                credit_value = DegreePlanService._safe_float(entry.get("credits") or entry.get("hours"))
            else:
                label = str(entry)
                code = None
                credit_value = None

            if not code:
                candidates = extract_codes_from_text(label)
                code = next(iter(sorted(candidates)), None)

            normalized_code = (code or "").upper().strip()
            if not normalized_code:
                continue

            normalized.append({
                "code": normalized_code,
                "label": label or normalized_code,
                "credits": credit_value if credit_value and credit_value > 0 else None,
            })

        return normalized

    @classmethod
    def _extract_concentration_definitions(cls, group: dict) -> List[dict]:
        if not isinstance(group, dict):
            return []

        container = None
        for key in cls.CONCENTRATION_CONTAINER_KEYS:
            value = group.get(key)
            if value:
                container = value
                break

        if not container:
            return []

        def _iter_named_payloads(data):
            if isinstance(data, dict):
                for name, payload in data.items():
                    yield name, payload
            elif isinstance(data, list):
                for payload in data:
                    if isinstance(payload, dict):
                        name = payload.get("name") or payload.get("title")
                        yield name, payload

        definitions = []
        for name, payload in _iter_named_payloads(container):
            blocks = payload if isinstance(payload, list) else [payload]
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                choose_from = (
                    block.get("choose_any")
                    or block.get("choose")
                    or block.get("options")
                    or block.get("courses")
                    or block.get("choices")
                )
                if not choose_from:
                    continue

                normalized_courses = cls._normalize_concentration_course_options(choose_from)
                if not normalized_courses:
                    continue

                required_hours = (
                    cls._safe_float(
                        block.get("hours_needed")
                        or block.get("requiredHours")
                        or block.get("requiredCredits")
                        or group.get("hoursPerConcentration")
                        or group.get("concentrationHours"),
                        12.0,
                    )
                    or 12.0
                )

                definition_name = (
                    name
                    or block.get("name")
                    or block.get("title")
                    or group.get("title")
                    or "Concentration Option"
                )

                definitions.append({
                    "name": definition_name,
                    "courses": normalized_courses,
                    "requiredHours": required_hours,
                    "selected": bool(block.get("selected") or block.get("active")),
                })

        return definitions

    @classmethod
    def _handle_concentration_group(cls, group: dict, completed_codes: Set[str], completed_hours: dict):
        definitions = cls._extract_concentration_definitions(group)
        if not definitions:
            return None

        group_type = cls._detect_focus_area_type(group)
        active_names = cls._collect_active_concentration_names(group)
        active_options = []

        for definition in definitions:
            definition_name = definition.get("name") or "Concentration Option"
            normalized_name = definition_name.upper().strip()
            taken_courses = [
                course
                for course in definition["courses"]
                if course["code"] in completed_codes
            ]
            completed_total = sum(
                completed_hours.get(course["code"], course.get("credits") or 3.0)
                for course in taken_courses
            )
            required_hours = definition.get("requiredHours") or 12.0
            satisfied = completed_total + 0.001 >= required_hours

            is_active = (
                definition.get("selected")
                or (active_names and normalized_name in active_names)
                or bool(taken_courses)
            )

            option_entry = {
                "name": definition_name,
                "requiredHours": required_hours,
                "completedHours": round(completed_total, 2),
                "remainingHours": max(0.0, round(required_hours - completed_total, 2)),
                "takenCourses": [course["label"] for course in taken_courses],
                "missingCourses": [
                    course["label"]
                    for course in definition["courses"]
                    if course["code"] not in completed_codes
                ],
                "satisfied": satisfied,
            }

            if is_active:
                active_options.append(option_entry)

        if not active_options:
            return None

        required_slots = len(active_options)
        satisfied_slots = sum(1 for option in active_options if option["satisfied"])
        issues = []

        for option in active_options:
            if option["satisfied"]:
                continue
            scope_label = group_type.lower()
            issues.append({
                "requirementId": f"{group.get('title') or group.get('id')}: {option['name']}",
                "message": (
                    f"{option['name']} {scope_label} needs "
                    f"{option['remainingHours']:g} more hour(s)"
                ),
                "missingCourses": option["missingCourses"],
                "category": group_type,
            })

        summary_entry = {
            "groupId": group.get("id") or group.get("title"),
            "title": group.get("title") or "Concentration",
            "requiredSelections": required_slots,
            "satisfiedSelections": satisfied_slots,
            "groupType": group_type,
            "options": active_options,
        }

        return summary_entry, issues, required_slots, min(satisfied_slots, required_slots)

    @classmethod
    def _build_concentration_summary(
        cls,
        groups: List[dict],
        completed_codes: Set[str],
        completed_hours: dict,
        focus_types: Optional[Set[str]] = None,
    ) -> List[dict]:
        normalized_focus = {ft.upper() for ft in focus_types} if focus_types else None
        summary = []
        for group in groups or []:
            result = cls._handle_concentration_group(group, completed_codes, completed_hours)
            if result:
                summary_entry, _, _, _ = result
                focus_type = (summary_entry.get("groupType") or "CONCENTRATION").upper()
                if normalized_focus and focus_type not in normalized_focus:
                    continue
                summary.append(summary_entry)
        return summary

    @classmethod
    def _attach_concentration_summary(cls, record: DegreePlanValidation):
        if not record:
            return
        existing_concentrations = getattr(record, "concentrations", None)
        existing_minors = getattr(record, "minors", None)
        if existing_concentrations is not None and existing_minors is not None:
            return

        requirement = getattr(record, "requirementSet", None)
        context = getattr(record, "context", None)
        if not requirement or not context:
            if existing_concentrations is None:
                record.concentrations = []
            if existing_minors is None:
                record.minors = []
            return

        completed_courses = context.completedCourses or []
        completed_codes = {
            (course.get("code") or "").upper().strip()
            for course in completed_courses
            if isinstance(course, dict)
        }
        completed_hours = cls._build_completed_course_credit_map(completed_courses)
        if existing_concentrations is None:
            record.concentrations = cls._build_concentration_summary(
                requirement.requirementData or [],
                completed_codes,
                completed_hours,
                {"CONCENTRATION"},
            )
        if existing_minors is None:
            record.minors = cls._build_concentration_summary(
                requirement.requirementData or [],
                completed_codes,
                completed_hours,
                {"MINOR"},
            )

    @classmethod
    def _attach_general_education_summary(cls, record: DegreePlanValidation):
        if not record:
            return
        if getattr(record, "generalEducation", None) is not None:
            return

        requirement = getattr(record, "requirementSet", None)
        context = getattr(record, "context", None)
        if not requirement or not context:
            record.generalEducation = []
            if getattr(record, "generalEducationRequirementCount", None) is None:
                record.generalEducationRequirementCount = 0
            if getattr(record, "generalEducationSatisfiedCount", None) is None:
                record.generalEducationSatisfiedCount = 0
            if getattr(record, "generalEducationCompletionPercent", None) is None:
                record.generalEducationCompletionPercent = 0.0
            return

        completed_courses = context.completedCourses or []
        completed_codes = {
            (course.get("code") or "").upper().strip()
            for course in completed_courses
            if isinstance(course, dict)
        }
        summary, required_total, satisfied_total = cls._build_general_education_summary(
            requirement.requirementData or [],
            completed_codes,
        )
        record.generalEducation = summary
        if getattr(record, "generalEducationRequirementCount", None) is None:
            record.generalEducationRequirementCount = required_total
        if getattr(record, "generalEducationSatisfiedCount", None) is None:
            record.generalEducationSatisfiedCount = satisfied_total
        if getattr(record, "generalEducationCompletionPercent", None) is None:
            record.generalEducationCompletionPercent = (
                round((satisfied_total / required_total) * 100, 2)
                if required_total
                else 0.0
            )

    @classmethod
    def _attach_general_education_metrics(cls, record: DegreePlanValidation):
        if not record:
            return

        summary = getattr(record, "generalEducation", None)
        if summary is None:
            cls._attach_general_education_summary(record)
            summary = getattr(record, "generalEducation", None)

        required_total = getattr(record, "generalEducationRequirementCount", None)
        satisfied_total = getattr(record, "generalEducationSatisfiedCount", None)
        completion_percent = getattr(record, "generalEducationCompletionPercent", None)

        needs_metrics = (
            required_total is None
            or satisfied_total is None
            or completion_percent is None
        )

        if not needs_metrics:
            return

        required_total = 0
        satisfied_total = 0
        for entry in summary or []:
            required = max(0, cls._safe_int(entry.get("requiredSelections"), 0))
            satisfied = max(0, cls._safe_int(entry.get("satisfiedSelections"), 0))
            required_total += required
            satisfied_total += min(required, satisfied)

        completion_percent = (
            round((satisfied_total / required_total) * 100, 2)
            if required_total
            else 0.0
        )

        if getattr(record, "generalEducationRequirementCount", None) is None:
            record.generalEducationRequirementCount = required_total
        if getattr(record, "generalEducationSatisfiedCount", None) is None:
            record.generalEducationSatisfiedCount = satisfied_total
        if getattr(record, "generalEducationCompletionPercent", None) is None:
            record.generalEducationCompletionPercent = completion_percent

    @classmethod
    def _attach_concentration_metrics(cls, record: DegreePlanValidation):
        if not record:
            return

        summary = getattr(record, "concentrations", None)
        if summary is None:
            cls._attach_concentration_summary(record)
            summary = getattr(record, "concentrations", None)

        if getattr(record, "concentrationIssues", None) is None:
            record.concentrationIssues = []

        required_total = getattr(record, "concentrationRequirementCount", None)
        satisfied_total = getattr(record, "concentrationSatisfiedCount", None)
        completion_percent = getattr(record, "concentrationCompletionPercent", None)

        needs_metrics = (
            required_total is None
            or satisfied_total is None
            or completion_percent is None
        )

        if not needs_metrics:
            return

        required_total = 0
        satisfied_total = 0
        for entry in summary or []:
            required = max(0, cls._safe_int(entry.get("requiredSelections"), 0))
            satisfied = max(0, cls._safe_int(entry.get("satisfiedSelections"), 0))
            required_total += required
            satisfied_total += min(required, satisfied)

        completion_percent = (
            round((satisfied_total / required_total) * 100, 2)
            if required_total
            else 0.0
        )

        if getattr(record, "concentrationRequirementCount", None) is None:
            record.concentrationRequirementCount = required_total
        if getattr(record, "concentrationSatisfiedCount", None) is None:
            record.concentrationSatisfiedCount = satisfied_total
        if getattr(record, "concentrationCompletionPercent", None) is None:
            record.concentrationCompletionPercent = completion_percent

    @classmethod
    def _attach_minor_metrics(cls, record: DegreePlanValidation):
        if not record:
            return

        summary = getattr(record, "minors", None)
        if summary is None:
            cls._attach_concentration_summary(record)
            summary = getattr(record, "minors", None)

        if getattr(record, "minorIssues", None) is None:
            record.minorIssues = []

        required_total = getattr(record, "minorRequirementCount", None)
        satisfied_total = getattr(record, "minorSatisfiedCount", None)
        completion_percent = getattr(record, "minorCompletionPercent", None)

        needs_metrics = (
            required_total is None
            or satisfied_total is None
            or completion_percent is None
        )

        if not needs_metrics:
            return

        required_total = 0
        satisfied_total = 0
        for entry in summary or []:
            required = max(0, cls._safe_int(entry.get("requiredSelections"), 0))
            satisfied = max(0, cls._safe_int(entry.get("satisfiedSelections"), 0))
            required_total += required
            satisfied_total += min(required, satisfied)

        completion_percent = (
            round((satisfied_total / required_total) * 100, 2)
            if required_total
            else 0.0
        )

        if getattr(record, "minorRequirementCount", None) is None:
            record.minorRequirementCount = required_total
        if getattr(record, "minorSatisfiedCount", None) is None:
            record.minorSatisfiedCount = satisfied_total
        if getattr(record, "minorCompletionPercent", None) is None:
            record.minorCompletionPercent = completion_percent

    @staticmethod
    def _ensure_major_metrics(record: DegreePlanValidation):
        if not record:
            return
        if getattr(record, "majorRequirementCount", None) is None:
            record.majorRequirementCount = 0
        if getattr(record, "majorSatisfiedCount", None) is None:
            record.majorSatisfiedCount = 0
        if getattr(record, "majorCompletionPercent", None) is None:
            record.majorCompletionPercent = 0.0



    @staticmethod
    def _evaluate_course_prerequisites(course: dict, completed_codes: Set[str]):
        warnings = []
        clauses = course.get("prerequisites") or []
        if not clauses:
            return warnings

        # Build a local copy we can extend with assumed completions (corequisites).
        effective_completed = {
            (code or "").upper().strip()
            for code in (completed_codes or set())
        }

        course_code = (course.get("code") or "").upper().strip()
        course_label = course_code or (course.get("title") or "Requirement")

        for clause in clauses:
            clause_type = str(clause.get("type") or "PREREQUISITE").upper()
            options = clause.get("options") or []
            if not options:
                continue

            normalized_options = [
                [code.upper() for code in (option or [])]
                for option in options
            ]

            if DegreePlanService._is_corequisite_clause(clause_type):
                # Assume corequisites will be satisfied concurrently and treat them as completed.
                for normalized in normalized_options:
                    effective_completed.update(normalized)
                continue

            satisfied = False
            for normalized in normalized_options:
                if all(code in effective_completed for code in normalized):
                    satisfied = True
                    break

            if satisfied:
                continue

            labels = [" + ".join(opt) for opt in options if opt]
            snippet = clause.get("text")
            message = f"{course_label} missing {clause_type.replace('_', ' ').lower()} requirements"
            if snippet:
                message = f"{message}: {snippet.strip()}"

            warnings.append({
                "requirementId": course_code or course_label,
                "message": message,
                "missingCourses": labels,
                "severity": "WARNING",
                "category": "PREREQUISITE",
            })

        return warnings

    @staticmethod
    def _normalize_program_code(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        v = value.replace(" ", "-").strip().upper()
        return v or None

    @staticmethod
    def _infer_catalog_year(profile: AdviseeProfile) -> str:
        raw = (profile.degree_plan or "").strip()
        if not raw:
            return DEFAULT_CATALOG_YEAR

        m = CATALOG_YEAR_PATTERN.search(raw)
        if m:
            start, end = m.group(1), m.group(2)
            return f"{start}-{end}" if end else start

        up = raw.upper()
        if up.startswith("CAT"):
            return up

        return DEFAULT_CATALOG_YEAR

    @staticmethod
    def _build_keywords(*terms: Optional[str]) -> List[str]:
        keywords = []
        for t in terms:
            if not t:
                continue
            tokens = re.split(r"[\s,/._-]+", t)
            keywords.extend(tok for tok in tokens if tok)
        return keywords

    @staticmethod
    def _build_catalog_seed_url(program_code: Optional[str], catalog_year: Optional[str]):
        terms = [program_code or "", catalog_year or "", "degree plan pdf"]
        query = "+".join(quote_plus(t.strip()) for t in terms if t and t.strip())

        if "{query}" in CATALOG_SEARCH_URL:
            return CATALOG_SEARCH_URL.format(query=query or "degree+plan")

        suffix = "" if CATALOG_SEARCH_URL.endswith(("?", "&")) else (
            "&" if "?" in CATALOG_SEARCH_URL else "?"
        )
        return f"{CATALOG_SEARCH_URL}{suffix}{query}"

    @classmethod
    def _bootstrap_context(cls, db: Session, advisee_id: int):
        profile = (
            db.query(AdviseeProfile)
            .filter(AdviseeProfile.adviseeID == advisee_id)
            .first()
        )
        if not profile:
            return False

        program_hint = (profile.degree_plan or "").strip()
        major_code = (profile.major or "").strip()
        if not (program_hint or major_code):
            return False

        catalog_year = cls._infer_catalog_year(profile)
        keywords = cls._build_keywords(program_hint, major_code, catalog_year)
        seed_url = cls._build_catalog_seed_url(program_hint or major_code, catalog_year)

        try:
            import_degree_plan_from_pdf_url(
                db,
                advisee_id,
                pdf_url=seed_url,
                required_keywords=keywords,
                create_validation=False,
            )
            return True
        except Exception as exc:
            logging.warning(
                "Degree plan bootstrap failed for advisee %s: %s",
                advisee_id,
                exc,
            )
            return False

    @classmethod
    def _ensure_context(cls, db: Session, advisee_id: int):
        profile = (
            db.query(AdviseeProfile)
            .filter(AdviseeProfile.adviseeID == advisee_id)
            .first()
        )
        context = load_context(db, advisee_id)

        requirement = (
            db.query(DegreeRequirementSet)
            .filter(
                DegreeRequirementSet.requirementSetID == context.requirementSetID
            )
            .first()
            if context else None
        )

        desired_code = cls._normalize_program_code(
            (profile.degree_plan or profile.major) if profile else None
        )
        requirement_code = cls._normalize_program_code(
            requirement.programCode if requirement else None
        )
        manual_requirement = requirement if cls._is_manual_requirement(requirement, advisee_id) else None
        if not manual_requirement:
            manual_requirement = cls._load_manual_requirement(db, advisee_id)

        if not context and manual_requirement:
            context = AdviseeDegreeContext(
                adviseeID=advisee_id,
                requirementSetID=manual_requirement.requirementSetID,
                completedCourses=[],
            )
            db.add(context)
            db.commit()
            db.refresh(context)
            requirement = manual_requirement
            requirement_code = cls._normalize_program_code(manual_requirement.programCode)

        needs_bootstrap = (
            not manual_requirement
            and (
                not context
                or not requirement
                or (desired_code and requirement_code and desired_code != requirement_code)
            )
        )

        if needs_bootstrap:
            if cls._bootstrap_context(db, advisee_id):
                context = load_context(db, advisee_id)
                if context:
                    requirement = (
                        db.query(DegreeRequirementSet)
                        .filter(
                            DegreeRequirementSet.requirementSetID == context.requirementSetID
                        )
                        .first()
                    )
                    if cls._is_manual_requirement(requirement, advisee_id):
                        manual_requirement = requirement

        return profile, context, requirement

    # ----------------------------------------
    # COURSE COLLECTION
    # ----------------------------------------
    @staticmethod
    def _collect_courses_from_schedules(db: Session, advisee_id: int):
        schedules = (
            db.query(Schedule)
            .options(
                joinedload(Schedule.term),
                joinedload(Schedule.classes)
                .joinedload(Class.section)
                .joinedload(Section.course),
            )
            .filter(Schedule.adviseeID == advisee_id)
            .order_by(
                case(
                    (Schedule.status == ScheduleStatusEnum.APPROVED, 0),
                    else_=1
                ),
                Schedule.createdWhen.desc(),
            )
            .all()
        )

        result = []
        seen_sections = set()

        for sched in schedules:
            term_label = sched.term.code if sched.term else None
            is_completed = (
                sched.status.value == ScheduleStatusEnum.APPROVED.value
            )
            status = "COMPLETED" if is_completed else "PLANNED"

            for cls in sched.classes:
                if cls.sectionID in seen_sections:
                    continue
                seen_sections.add(cls.sectionID)

                section = cls.section
                course = section.course if section else None

                code = ""
                if course and course.courseName:
                    code = course.courseName.strip()
                elif section and section.crn:
                    code = str(section.crn)

                title = course.courseName if course else None
                if course and course.description:
                    title = course.description
                elif not title and section and section.description:
                    title = section.description

                credits = 0
                if course and course.credits:
                    try:
                        credits = float(course.credits)
                    except:
                        credits = 0
                if credits <= 0:
                    credits = 3.0

                result.append({
                    "code": code or f"CLASS-{cls.classID}",
                    "title": title,
                    "credits": credits,
                    "term": term_label,
                    "status": status,
                })

        return serialize_courses(result)

    @staticmethod
    def _collect_courses_from_transcript(db: Session, advisee_id: int):
        enrollments = TranscriptService._load_enrollments(db, advisee_id)
        if not enrollments:
            return []

        terms = TranscriptService._build_terms(enrollments)
        completed = []

        for term in terms:
            for c in term.courses:
                if (c.status or "").lower() != "completed":
                    continue

                code_candidates = extract_codes_from_text(
                    " ".join(x for x in [
                        getattr(c, "courseCode", None),
                        getattr(c, "courseTitle", None),
                    ] if x)
                )

                normalized = next(iter(sorted(code_candidates)), None)
                if not normalized:
                    normalized = (getattr(c, "courseCode", "") or "").upper()

                completed.append({
                    "code": normalized,
                    "title": getattr(c, "courseTitle", None),
                    "credits": float(c.credits or 0),
                    "term": term.term,
                    "status": "COMPLETED",
                })

        return completed

    # ----------------------------------------
    # CONTEXT / REQUIREMENT SET API
    # ----------------------------------------
    @staticmethod
    def create_requirement_set(db: Session, payload: DegreeRequirementSetCreate):
        groups = [g.dict() for g in payload.requirementGroups]
        record = DegreeRequirementSet(
            programCode=payload.programCode,
            catalogYear=payload.catalogYear,
            programName=payload.programName,
            totalCredits=payload.totalCredits,
            requirementData=groups,
            sourceDocument=payload.sourceDocument,
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = (
                db.query(DegreeRequirementSet)
                .filter(
                    DegreeRequirementSet.programCode == payload.programCode,
                    DegreeRequirementSet.catalogYear == payload.catalogYear,
                )
                .first()
            )
            if existing:
                return existing
            raise

        db.refresh(record)
        return record

    @staticmethod
    def list_requirement_sets(db: Session, program_code: Optional[str] = None):
        query = db.query(DegreeRequirementSet)
        if program_code:
            normalized = DegreePlanService._normalize_program_code(program_code)
            if normalized:
                query = query.filter(DegreeRequirementSet.programCode == normalized)
        return query.order_by(DegreeRequirementSet.updatedAt.desc()).all()

    @staticmethod
    def upsert_context(db: Session, advisee_id: int, payload: AdviseeContextUpsert):
        requirement = (
            db.query(DegreeRequirementSet)
            .filter(DegreeRequirementSet.requirementSetID == payload.requirementSetID)
            .first()
        )
        if not requirement:
            raise HTTPException(404, "Requirement set not found")

        context = load_context(db, advisee_id)
        if not context:
            context = AdviseeDegreeContext(
                adviseeID=advisee_id,
                requirementSetID=requirement.requirementSetID,
            )
            db.add(context)

        context.requirementSetID = requirement.requirementSetID
        context.completedCourses = serialize_courses(
            [c.dict() for c in payload.completedCourses]
        )
        context.overrides = payload.overrides
        context.notes = payload.notes

        db.commit()
        db.refresh(context)
        return context

    # ----------------------------------------
    # SUMMARY
    # ----------------------------------------
    @staticmethod
    def get_advisee_summary(db: Session, advisee_id: int):
        profile, context, requirement = DegreePlanService._ensure_context(db, advisee_id)
        student = profile
        student_payload = profile
        transcript_payload = None

        if profile:
            try:
                transcript_payload = TranscriptService.get_transcript_for_advisee(
                    db,
                    advisee_id,
                    {"role": "advisor"},
                )
            except HTTPException as exc:
                if exc.status_code != 404:
                    logging.warning(
                        "Failed to load transcript for advisee %s: %s",
                        advisee_id,
                        exc.detail if hasattr(exc, "detail") else exc,
                    )

        latest_validation = (
            db.query(DegreePlanValidation)
            .filter(DegreePlanValidation.adviseeID == advisee_id)
            .order_by(DegreePlanValidation.createdAt.desc())
            .first()
        )
        latest_validation = DegreePlanService._normalize_validation_record(latest_validation)

        transcript_courses = DegreePlanService._collect_courses_from_transcript(db, advisee_id)
        schedule_courses = DegreePlanService._collect_courses_from_schedules(db, advisee_id)

        completed_courses = (
            transcript_courses if transcript_courses else schedule_courses
        )

        if context and completed_courses:
            context.completedCourses = completed_courses

        requirement_payload = None
        if requirement:
            requirement_payload = {
                "requirementSetID": requirement.requirementSetID,
                "programCode": (student.major if student else None) or requirement.programCode,
                "catalogYear": normalize_catalog_display(requirement.catalogYear),
                "programName": student.degree_plan or requirement.programName,
                "totalCredits": requirement.totalCredits,
                "requirementGroups": requirement.requirementData or [],
                "sourceDocument": requirement.sourceDocument,
                "createdAt": requirement.createdAt,
                "updatedAt": requirement.updatedAt,
            }


        return {
            "context": context,
            "requirementSet": requirement_payload,
            "latestValidation": latest_validation,
            "student": student_payload,
            "transcript": transcript_payload,
        }

    # ----------------------------------------
    # VALIDATION MANAGEMENT
    # ----------------------------------------
    @staticmethod
    def list_validations(db: Session, advisee_id: int):
        records = (
            db.query(DegreePlanValidation)
            .filter(DegreePlanValidation.adviseeID == advisee_id)
            .order_by(DegreePlanValidation.createdAt.desc())
            .all()
        )
        return [
            DegreePlanService._normalize_validation_record(record)
            for record in records
        ]

    @classmethod
    def enqueue_validation(
        cls,
        db: Session,
        advisee_id: int,
        run_type: ValidationRunType = ValidationRunType.MANUAL,
        triggered_by: Optional[int] = None,
        background_tasks: Optional[BackgroundTasks] = None,
    ):
        _, context, requirement = cls._ensure_context(db, advisee_id)

        if not context or not requirement:
            raise HTTPException(404, "No degree plan context is linked to this advisee")

        normalized_run_type = (
            run_type if isinstance(run_type, ValidationRunType) else ValidationRunType(run_type)
        )

        validation = DegreePlanValidation(
            adviseeID=advisee_id,
            contextID=context.contextID,
            requirementSetID=requirement.requirementSetID,
            status=ValidationStatus.PENDING,
            runType=normalized_run_type,
            triggeredBy=triggered_by,
        )

        db.add(validation)
        db.commit()
        db.refresh(validation)

        if background_tasks:
            background_tasks.add_task(process_validation_job, validation.validationID)
        else:
            process_validation_job(validation.validationID)
            db.refresh(validation)

        return cls._normalize_validation_record(validation)

    # ----------------------------------------
    # VALIDATION CORE
    # ----------------------------------------
    @staticmethod
    def _process_validation(db: Session, validation_id: int):
        validation = (
            db.query(DegreePlanValidation)
            .filter(DegreePlanValidation.validationID == validation_id)
            .first()
        )
        if not validation:
            return

        validation.status = ValidationStatus.RUNNING
        validation.startedAt = datetime.utcnow()
        db.commit()

        context = validation.context
        requirement = validation.requirementSet

        if not context or not requirement:
            validation.status = ValidationStatus.ERROR
            validation.message = "Missing requirement data"
            validation.finishedAt = datetime.utcnow()
            validation.issues = []
            db.commit()
            return

        # --- Collect completed courses ---
        transcript = DegreePlanService._collect_courses_from_transcript(db, validation.adviseeID)
        context_courses = context.completedCourses or []
        completed_courses = merge_completed_sources(transcript, context_courses)
        context.completedCourses = completed_courses

        completed_codes = {
            (c.get("code") or "").upper().strip()
            for c in completed_courses
        }
        completed_codes |= DegreePlanService._collect_assumed_corequisites(requirement.requirementData)
        completed_codes |= DegreePlanService._collect_zero_level_courses(requirement.requirementData)
        completed_course_hours = DegreePlanService._build_completed_course_credit_map(completed_courses)

        groups = requirement.requirementData or []
        group_results = []
        core_issues = []
        prereq_warnings = []
        total_items = 0
        satisfied_items = 0
        concentration_summaries = []
        concentration_issues = []
        concentration_required_total = 0
        concentration_satisfied_total = 0
        minor_summaries = []
        minor_issues = []
        minor_required_total = 0
        minor_satisfied_total = 0
        general_ed_summaries = []
        general_ed_required_total = 0
        general_ed_satisfied_total = 0
        requirement_scope_totals = {
            "MAJOR": {"total": 0, "satisfied": 0},
            "MINOR": {"total": 0, "satisfied": 0},
            "CONCENTRATION": {"total": 0, "satisfied": 0},
        }

        # ----------------------------------------
        # Validate each requirement group
        # ----------------------------------------
        for group in groups:
            title = group.get("title", "")
            description = group.get("description", "")
            group_courses = group.get("courses", [])
            group_id = group.get("id") or title
            group_scope = DegreePlanService._determine_requirement_scope(group)
            group_entry = {
                "id": group_id,
                "title": title,
                "missing": False,
                "suggestions": [],
                "satisfied": True,
            }

            if DegreePlanService._is_general_program_note(title, description):
                continue

            general_ed_result = DegreePlanService._handle_general_education_group(
                group,
                completed_codes,
            )
            if general_ed_result:
                summary_entry, required_slots, satisfied_slots = general_ed_result
                general_ed_summaries.append(summary_entry)
                general_ed_required_total += required_slots
                general_ed_satisfied_total += satisfied_slots
                missing_slots = max(0, required_slots - satisfied_slots)
                group_entry["missing"] = missing_slots > 0
                group_entry["satisfied"] = missing_slots == 0
                group_entry["suggestions"] = (
                    [f"Need {missing_slots:g} more selection(s) from {title}"]
                    if missing_slots
                    else []
                )
                group_results.append(group_entry)
                continue

            concentration_result = DegreePlanService._handle_concentration_group(
                group,
                completed_codes,
                completed_course_hours,
            )
            if concentration_result:
                summary_entry, concentration_messages, required_slots, satisfied_slots = concentration_result
                focus_type = (summary_entry.get("groupType") or "CONCENTRATION").upper()
                if focus_type == "MINOR":
                    minor_summaries.append(summary_entry)
                    minor_required_total += required_slots
                    minor_satisfied_total += satisfied_slots
                    if concentration_messages:
                        minor_issues.extend(concentration_messages)
                else:
                    concentration_summaries.append(summary_entry)
                    concentration_required_total += required_slots
                    concentration_satisfied_total += satisfied_slots
                    if concentration_messages:
                        concentration_issues.extend(concentration_messages)
                missing = satisfied_slots < required_slots
                group_entry["missing"] = missing
                group_entry["satisfied"] = not missing
                suggestions = [
                    msg.get("message")
                    for msg in (concentration_messages or [])
                    if isinstance(msg, dict) and msg.get("message")
                ]
                group_entry["suggestions"] = suggestions
                group_results.append(group_entry)
                continue

            # DETECT CATEGORY REQUIREMENT
            category_rule = detect_category_from_group(title, description)
            if not category_rule:
                category_rule = detect_category_from_courses(group_courses)

            # ----------------------------------------
            # CATEGORY MODE
            # ----------------------------------------
            if category_rule:
                total_items += 1
                scope_tracker = requirement_scope_totals.get(group_scope, requirement_scope_totals["MAJOR"])
                scope_tracker["total"] += 1
                satisfied = completed_satisfies_category(category_rule, completed_courses)

                # If any of the explicitly listed courses satisfy it
                if not satisfied:
                    acceptable_codes = set()
                    for c in group_courses:
                        acceptable_codes |= expand_requirement_codes(c or {}, description)
                    if acceptable_codes & completed_codes:
                        satisfied = True

                if satisfied:
                    satisfied_items += 1
                    scope_tracker["satisfied"] += 1
                    group_entry["missing"] = False
                    group_entry["satisfied"] = True
                    group_entry["suggestions"] = []
                    group_results.append(group_entry)
                    continue

                label = CATEGORY_RULES[category_rule]["label"]
                core_issues.append({
                    "requirementId": group_id,
                    "message": f"Missing: {label}",
                    "missingCourses": [label],
                    "category": group_scope,
                })
                group_entry["missing"] = True
                group_entry["satisfied"] = False
                group_entry["suggestions"] = [f"Missing: {label}"]
                group_results.append(group_entry)
                continue

            # ----------------------------------------
            # SPECIFIC COURSE MODE
            # ----------------------------------------
            required_credits = 0.0
            try:
                required_credits = float(group.get("requiredCredits") or 0)
            except:
                required_credits = 0.0

            missing_entries = []
            group_total_credits = 0.0
            satisfied_credits = 0.0
            entries_count = 0
            satisfied_count = 0
            used_codes = set()

            # Collect requirement entries
            for course in group_courses:
                course_code = (course.get("code") or "").upper().strip()
                if course_code and course_code not in completed_codes:
                    prereq_warnings.extend(
                        DegreePlanService._evaluate_course_prerequisites(course, completed_codes)
                    )

                expanded = expand_requirement_codes(course, description)
                if not expanded:
                    continue  # optional descriptor-only course

                entries_count += 1

                credit = 0.0
                try:
                    credit = float(course.get("credits") or 0)
                except:
                    credit = 0.0
                if credit <= 0:
                    credit = 3.0

                group_total_credits += credit

                matched = next((code for code in expanded if code in completed_codes), None)

                if matched:
                    if matched not in used_codes:
                        used_codes.add(matched)
                        satisfied_credits += credit
                        satisfied_count += 1
                    continue

                missing_entries.append("/".join(sorted(expanded)))

            # Determine if credit-based choice group
            is_choice = (
                required_credits > 0
                and group_total_credits > required_credits + 0.01
            )

            if is_choice:
                avg_credit = group_total_credits / entries_count if entries_count else 0
                if avg_credit <= 0:
                    avg_credit = 3.0

                needed = max(1, math.ceil(required_credits / avg_credit))
                needed = min(needed, entries_count)

                total_items += needed
                satisfied_match = min(satisfied_count, needed)
                satisfied_items += satisfied_match
                scope_tracker = requirement_scope_totals.get(group_scope, requirement_scope_totals["MAJOR"])
                scope_tracker["total"] += needed
                scope_tracker["satisfied"] += satisfied_match

                gap_message = None
                if satisfied_credits < required_credits:
                    remain = max(0, round(required_credits - satisfied_credits, 2))
                    gap_message = f"Need {remain:g} more credit(s) from {title}"
                    core_issues.append({
                        "requirementId": group_id,
                        "message": gap_message,
                        "missingCourses": [
                            f"{title}: additional {remain:g} credit(s) needed"
                        ],
                        "category": group_scope,
                    })
                group_entry["missing"] = gap_message is not None
                group_entry["satisfied"] = gap_message is None
                group_entry["suggestions"] = [gap_message] if gap_message else []
                group_results.append(group_entry)
                continue

            # Normal required-course list mode
            total_items += entries_count
            satisfied_items += satisfied_count
            scope_tracker = requirement_scope_totals.get(group_scope, requirement_scope_totals["MAJOR"])
            scope_tracker["total"] += entries_count
            scope_tracker["satisfied"] += satisfied_count

            missing = bool(missing_entries)
            group_entry["missing"] = missing
            group_entry["satisfied"] = not missing
            group_entry["suggestions"] = missing_entries if missing_entries else []
            if missing_entries:
                core_issues.append({
                    "requirementId": group_id,
                    "message": f"Missing {len(missing_entries)} requirement(s) in {title}",
                    "missingCourses": missing_entries,
                    "category": group_scope,
                })
            group_results.append(group_entry)

        # ----------------------------------------
        # COMPLETION %
        # ----------------------------------------
        if total_items > 0:
            completion = round((satisfied_items / total_items) * 100, 2)
        else:
            completion = 0.0

        if concentration_required_total > 0:
            concentration_completion = round(
                (concentration_satisfied_total / concentration_required_total) * 100,
                2,
            )
        else:
            concentration_completion = 0.0

        validation_result_payload = {
            "completionPercent": completion,
            "issues": core_issues + prereq_warnings,
            "groupResults": group_results,
        }

        llm_breakdown = None
        if requirement and context:
            try:
                llm_breakdown = classify_course_breakdown(
                    requirement,
                    completed_courses,
                    validation_result_payload,
                )
            except Exception as exc:  # pragma: no cover - best-effort logging
                logging.warning(
                    "LLM course breakdown failed for advisee %s: %s",
                    validation.adviseeID,
                    exc,
                )
        validation.llmCourseBreakdown = llm_breakdown


        validation.completionPercent = completion
        validation.issues = core_issues + prereq_warnings
        validation.status = ValidationStatus.PASSED if not core_issues else ValidationStatus.FAILED
        validation.message = (
            "All requirements satisfied." if not core_issues else "Outstanding requirements."
        )
        validation.finishedAt = datetime.utcnow()
        validation.concentrations = concentration_summaries
        validation.concentrationIssues = concentration_issues
        validation.concentrationRequirementCount = concentration_required_total
        validation.concentrationSatisfiedCount = concentration_satisfied_total
        validation.concentrationCompletionPercent = concentration_completion
        validation.minors = minor_summaries
        validation.minorIssues = minor_issues
        if general_ed_required_total > 0:
            general_ed_completion = round(
                (general_ed_satisfied_total / general_ed_required_total) * 100,
                2,
            )
        else:
            general_ed_completion = 0.0

        validation.generalEducation = general_ed_summaries
        validation.generalEducationRequirementCount = general_ed_required_total
        validation.generalEducationSatisfiedCount = general_ed_satisfied_total
        validation.generalEducationCompletionPercent = general_ed_completion

        major_total = requirement_scope_totals["MAJOR"]["total"]
        major_satisfied = requirement_scope_totals["MAJOR"]["satisfied"]
        minor_general_total = requirement_scope_totals["MINOR"]["total"]
        minor_general_satisfied = requirement_scope_totals["MINOR"]["satisfied"]
        combined_minor_total = minor_required_total + minor_general_total
        combined_minor_satisfied = minor_satisfied_total + minor_general_satisfied

        validation.minorRequirementCount = combined_minor_total
        validation.minorSatisfiedCount = combined_minor_satisfied
        validation.minorCompletionPercent = (
            round((combined_minor_satisfied / combined_minor_total) * 100, 2)
            if combined_minor_total
            else 0.0
        )
        validation.majorRequirementCount = major_total
        validation.majorSatisfiedCount = major_satisfied
        validation.majorCompletionPercent = (
            round((major_satisfied / major_total) * 100, 2) if major_total else 0.0
        )

        db.commit()
        db.refresh(validation)


# ----------------------------------------
# JOB WRAPPER
# ----------------------------------------
def process_validation_job(validation_id: int):
    db = SessionLocal()
    try:
        DegreePlanService._process_validation(db, validation_id)
    finally:
        db.close()
