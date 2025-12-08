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
    "Your task is ONLY to determine which NON-CONCENTRATION courses the student "
    "has completed and which they still need.\n\n"

    "DO NOT choose or infer concentrations or minors.\n"
    "Concentration and minor selection is provided separately.\n\n"

    "OUTPUT RULES:\n"
    "Return ONLY a JSON object with the following structure:\n"
    "{\n"
    "  \"takenCourses\": [list of course codes],\n"
    "  \"neededCourses\": [list of course codes]\n"
    "}\n\n"

    "ADDITIONAL RULES:\n"
    "1. For ANY-OF requirement groups, output only ONE needed course.\n"
    "2. For category groups (Fine Arts, Humanities, etc.), if satisfied, output no needed courses.\n"
    "3. Only output actual required courses — no suggestions or examples.\n"
    "4. Output ONLY course codes, never titles.\n"
)


def _build_context_payload(
    requirement_set: DegreeRequirementSet,
    completed_courses: List[Dict[str, Any]],
    validation_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Provides ONLY the data needed for generic taken/needed evaluation.
    Concentration + Minor are NOT included (they are resolved internally).
    """

    raw_groups = getattr(requirement_set, "requirementData", []) or []

    # Strip concentration groups before sending to LLM
    filtered_groups = [
        g for g in raw_groups
        if str(g.get("type", "")).lower() != "concentration"
        and str(g.get("type", "")).lower() != "minor"
    ]

    return {
        "requirementSet": {
            "programName": getattr(requirement_set, "programName", "Unknown"),
            "catalogYear": getattr(requirement_set, "catalogYear", "Unknown"),
            "totalCredits": getattr(requirement_set, "totalCredits", None),
        },

        "completedCourses": [
            {"code": (c.get("code") or "").strip()}
            for c in completed_courses
            if isinstance(c, dict)
        ],

        # Send validation status ONLY for non-concentration groups
        "groupResults": [
            {
                "id": g.get("id"),
                "title": g.get("title"),
                "missing": g.get("missing"),
                "suggestions": g.get("suggestions"),
                "satisfied": g.get("satisfied"),
            }
            for g in validation_result.get("groupResults") or []
            if g.get("id") not in {cg.get("id") for cg in raw_groups if str(cg.get("type","")).lower()=="concentration"}
        ],

        # Requirement definitions — excluding concentration/minor
        "requirementRules": [
            {
                "id": group.get("id"),
                "title": group.get("title"),
                "requiredCredits": group.get("requiredCredits"),
                "courses": group.get("courses"),
                "category": group.get("category"),
                "type": group.get("type", "all")
            }
            for group in filtered_groups
        ],
    }


def _build_user_prompt(payload: Dict[str, Any]) -> str:
    payload_json = json.dumps(payload, default=str)
    return (
        "Analyze the following degree validation dataset and determine which NON-CONCENTRATION "
        "courses are taken and which are needed.\n\n"
        "You MUST ignore concentrations and minors—they are handled separately by the system.\n\n"
        "Return JSON only:\n"
        "{\n"
        "  \"takenCourses\": [],\n"
        "  \"neededCourses\": []\n"
        "}\n\n"
        f"Validation data:\n{payload_json}"
    )


def _extract_json(text: str):
    if not text:
        return None
    matches = re.findall(r"\{[\s\S]*\}", text)
    for candidate in matches:
        try:
            return json5.loads(candidate)
        except Exception:
            continue
    return None


def _normalize_course_list(raw_value: Any) -> List[str]:
    if not isinstance(raw_value, list):
        return []
    seen = set()
    out = []
    for item in raw_value:
        item = str(item).strip().upper()
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def classify_course_breakdown(
    requirement_set: DegreeRequirementSet,
    completed_courses: List[Dict[str, Any]],
    validation_result: Dict[str, Any],
) -> Optional[Dict[str, Any]]:

    # Pull concentration + minor already computed by validator
    concentration_block = validation_result.get("activeConcentrations") or []
    minor_block = validation_result.get("activeMinors") or []

    try:
        openai_service = get_openai_service()
    except RuntimeError as exc:
        logger.debug("OpenAI not configured: %s", exc)
        return None

    payload = _build_context_payload(requirement_set, completed_courses, validation_result)
    prompt = _build_user_prompt(payload)

    try:
        completion = openai_service.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_output_tokens=1500,
        )
    except Exception as exc:
        logger.warning("LLM call failed: %s", exc)
        return None

    try:
        content = completion.output[0].content[0].text
    except Exception as exc:
        logger.warning("Missing LLM content: %s", exc)
        return None

    data = _extract_json(content or "")
    if not data:
        logger.warning("Could not parse JSON from LLM output.")
        return None

    taken = _normalize_course_list(data.get("takenCourses"))
    needed = _normalize_course_list(data.get("neededCourses"))

    # ----------------------------------------------------------
    # Merge validator concentration/minor results
    # ----------------------------------------------------------
    output_concentration = (
        concentration_block[0]
        if isinstance(concentration_block, list) and concentration_block
        else {"name": None, "taken": [], "needed": []}
    )

    output_minor = (
        minor_block[0]
        if isinstance(minor_block, list) and minor_block
        else {"name": None, "taken": [], "needed": []}
    )

    return {
        "takenCourses": taken,
        "neededCourses": needed,
        "concentration": output_concentration,
        "minor": output_minor,
    }
