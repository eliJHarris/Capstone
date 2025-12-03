"""
Backwards-compatible re-exports for degree requirement models.
These models now live in models.degree_plan; importing from here keeps existing imports working
without duplicating table definitions.
"""

from models.degree_plan import (  # noqa: F401
    DegreeRequirementSet,
    AdviseeDegreeContext,
    DegreePlanValidation,
    ValidationStatus,
    ValidationRunType as RunType,
)
