import json
import json5
import logging
import re
from typing import Any, Dict, List, Optional

from models.degree_plan import DegreeRequirementSet
from services.openai_service import get_openai_service

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an expert academic advising assistant for the AdviseMe platform.\n"
    "You receive structured JSON describing:\n"
    "  - degree requirements\n"
    "  - requirement groups and categories\n"
    "  - completed coursework\n"
    "  - requirement satisfaction status\n"
    "Your task is to determine which courses the student has completed and which courses they still need to take.\n\n"

    "OUTPUT RULES:\n"
    "Return ONLY a JSON object with the following structure:\n"
    "{\n"
    "  \"takenCourses\": [list of course codes],\n"
    "  \"neededCourses\": [list of course codes],\n"
    "  \"concentration\": {\n"
    "     \"name\": <string|null>,\n"
    "     \"taken\": [list of course codes],\n"
    "     \"needed\": [list of course codes]\n"
    "  },\n"
    "  \"minor\": {\n"
    "     \"name\": <string|null>,\n"
    "     \"taken\": [list of course codes],\n"
    "     \"needed\": [list of course codes]\n"
    "  }\n"
    "}\n\n"

    "ADDITIONAL RULES:\n"
    "1. For requirement groups that list multiple possible options (ANY-OF groups), "
    "   if the student has completed ANY valid course from the group, treat the requirement as satisfied.\n"
    "   If UNSATISFIED, choose ONE needed course from the group. Do not list every possible option.\n\n"

    "2. For category-based requirements (e.g., Fine Arts, Humanities, Social Sciences), "
    "   match completed courses to category rules. If satisfied, no course is needed.\n\n"

    "3. Concentrations:\n"
    "   - If the requirement set contains concentration groups, detect which concentration applies "
    "     using group satisfaction, naming conventions, or course patterns.\n"
    "   - Only output ONE concentration (the student's active one).\n"
    "   - Output taken and needed courses for the chosen concentration.\n"
    "   - If the program has no concentration requirements, output name = null and empty lists.\n\n"

    "4. Minors:\n"
    "   - Same rules as concentrations.\n"
    "   - Output exactly one minor or null.\n\n"

    "5. takenCourses should list all courses that satisfy program requirements.\n"
    "6. neededCourses should list all remaining courses needed for degree completion.\n"
    "7. Only output course CODES (e.g., MKTG 3013). No titles, explanations, or commentary.\n"
    "8. Do not include classes that are suggested or examples in the degree plan unless they are explicitly required.\n"
)



def _build_context_payload(
    requirement_set: DegreeRequirementSet,
    completed_courses: List[Dict[str, Any]],
    validation_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Expanded payload including:
    - requirement rules
    - completed courses
    - validation group status
    - requirement groups used by the LLM for inference
    """

    # requirementData contains the raw requirement group definitions from DB
    raw_groups = getattr(requirement_set, "requirementData", []) or []

    return {
        "requirementSet": {
            "programName": getattr(requirement_set, "programName", "Unknown"),
            "catalogYear": getattr(requirement_set, "catalogYear", "Unknown"),
            "totalCredits": getattr(requirement_set, "totalCredits", None),
            "validationGroups": len(raw_groups),
        },

        # Provide completed courses
        "completedCourses": [
            {
                "code": (c.get("code") or "").strip(),
                "title": (c.get("title") or "").strip(),
                "term": c.get("term"),
            }
            for c in completed_courses
            if isinstance(c, dict)
        ],

        # Provide validation result group status so LLM knows which are satisfied
        "groupResults": [
            {
                "id": group.get("id"),
                "title": group.get("title"),
                "missing": group.get("missing"),
                "suggestions": group.get("suggestions"),
                "satisfied": group.get("satisfied"),
            }
            for group in validation_result.get("groupResults") or []
        ],

        # Expanded requirement rules for LLM reasoning
        "requirementRules": [
            {
                "id": group.get("id"),
                "title": group.get("title"),
                "requiredCredits": group.get("requiredCredits"),
                "courses": group.get("courses"),    # list of allowed course options
                "category": group.get("category"),  # e.g., "Fine Arts", "Humanities"
                "type": group.get("type", "all")    # "all", "any-of", "credits", "category"
            }
            for group in raw_groups
        ],

        "completionPercent": validation_result.get("completionPercent"),
        "issues": validation_result.get("issues") or [],
    }


def _build_user_prompt(payload: Dict[str, Any]) -> str:
    payload_json = json.dumps(payload, default=str)
    return (
        "Analyze the following degree validation dataset and determine which courses "
        "the student has already completed and which are still required to fulfill "
        "the degree, concentration, and minor requirements.\n\n"
        "Use the following strict JSON output format:\n"
        "{\n"
        "  \"takenCourses\": [],\n"
        "  \"neededCourses\": [],\n"
        "  \"concentration\": {\"name\": null, \"taken\": [], \"needed\": []},\n"
        "  \"minor\": {\"name\": null, \"taken\": [], \"needed\": []}\n"
        "}\n\n"
        "Important:\n"
        "- Only include actual required courses.\n"
        "- Elective groups should be satisfied by any one valid option.\n"
        "- Category requirements (Fine Arts, Humanities, etc.) should be satisfied "
        "  if the student has taken any qualifying course.\n"
        "- Choose only ONE concentration and ONE minor if applicable.\n"
        "- If concentration or minor does not apply, output name=null and empty lists.\n\n"
        f"Validation data:\n{payload_json}"
    )

def _extract_json(text: str):
    if not text:
        return None

    # Remove surrounding explanation if any
    # Extract the FIRST JSON object body using a regex that supports pretty JSON
    json_matches = re.findall(r"\{[\s\S]*\}", text)
    if not json_matches:
        return None

    for candidate in json_matches:
        try:
            # Use JSON5 to allow trailing commas, comments, newlines, and relaxed formatting
            return json5.loads(candidate)
        except Exception:
            continue

    return None


def _normalize_course_list(raw_value: Any) -> List[str]:
    if not isinstance(raw_value, list):
        return []
    seen = set()
    normalized = []
    for entry in raw_value:
        if not entry:
            continue
        code = str(entry).strip().upper()
        if code and code not in seen:
            seen.add(code)
            normalized.append(code)
    return normalized


def classify_course_breakdown(
    requirement_set: DegreeRequirementSet,
    completed_courses: List[Dict[str, Any]],
    validation_result: Dict[str, Any],
) -> Optional[Dict[str, List[str]]]:
    """
    Ask the LLM to summarize which courses are complete vs still needed.

    Handles:
    - category-based requirements
    - flexible elective groups
    - detecting the correct concentration or minor
    """
    try:
        openai_service = get_openai_service()
    except RuntimeError as exc:
        logger.debug("OpenAI not configured, skipping LLM course breakdown: %s", exc)
        return None

    payload = _build_context_payload(requirement_set, completed_courses, validation_result)
    prompt = _build_user_prompt(payload)

    try:
        completion = openai_service.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.15,
            max_output_tokens=2000,
        )
    except Exception as exc:
        logger.warning("LLM course breakdown call failed: %s", exc)
        return None

    try:
        content = completion.output[0].content[0].text
    except (AttributeError, IndexError) as exc:
        logger.warning("LLM response missing content: %s", exc)
        return None

    data = _extract_json(content or "")
    if not data:
        logger.warning("LLM response could not be parsed as JSON: %s", content)
        return None

    return {
        "takenCourses": _normalize_course_list(data.get("takenCourses")),
        "neededCourses": _normalize_course_list(data.get("neededCourses")),
    }
