from typing import Dict, Any, List


def format_requirement_groups(group_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert each requirement group into UI-friendly format:
    - id
    - title
    - satisfied / missing
    - suggestions
    """
    formatted = []

    for g in group_results or []:
        formatted.append({
            "id": g.get("id"),
            "title": g.get("title"),
            "satisfied": not g.get("missing", False),
            "missing": g.get("missing", False),
            "suggestions": g.get("suggestions") or [],
        })

    return formatted


def format_concentration_cards(active_concentrations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Each concentration becomes a UI card:
    {
        name,
        hoursRequired,
        taken,
        needed,
        satisfied
    }
    """
    cards = []

    for conc in active_concentrations or []:
        needed = conc.get("needed") or []
        cards.append({
            "name": conc.get("name") or conc.get("title"),
            "hoursRequired": conc.get("hoursRequired", 12),
            "taken": conc.get("taken", []),
            "needed": needed,
            "satisfied": len(needed) == 0,
        })

    return cards


def format_minor_card(minor_block: Dict[str, Any]) -> Dict[str, Any]:
    """
    Single minor card (or empty if program has none).
    """
    if not minor_block or not minor_block.get("name"):
        return {
            "name": None,
            "taken": [],
            "needed": [],
            "satisfied": True,
        }

    needed = minor_block.get("needed") or []

    return {
        "name": minor_block.get("name"),
        "taken": minor_block.get("taken", []),
        "needed": needed,
        "satisfied": len(needed) == 0,
    }


def build_ui_degree_payload(
    validation_result: Dict[str, Any],
    llm_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Combine:
     - validator results
     - validator concentration/minor evaluation
     - LLM taken/needed for non-concentration requirements

    Return a single clean JSON structure for UI.
    """

    group_results = validation_result.get("groupResults") or []
    concentration_results = validation_result.get("concentrations") or []
    minor_results = validation_result.get("minors") or []

    taken = llm_result.get("takenCourses", [])
    needed = llm_result.get("neededCourses", [])

    ui_payload = {
        "summary": {
            "completionPercent": validation_result.get("completionPercent"),
            "majorCompletion": validation_result.get("majorCompletionPercent"),
            "concentrationCompletion": validation_result.get("concentrationCompletionPercent"),
            "minorCompletion": validation_result.get("minorCompletionPercent"),
            "generalEducationCompletion": validation_result.get("generalEducationCompletionPercent"),
        },

        "requirements": format_requirement_groups(group_results),

        "concentrations": format_concentration_cards(
            validation_result.get("concentrations") or []
        ),

        "minor": format_minor_card(
            minor_results[0] if minor_results else None
        ),

        "taken": taken,
        "needed": needed,
    }

    return ui_payload
