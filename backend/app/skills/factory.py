from app.skills.definitions import (
    PROPOSAL_ANALYSIS_SKILL,
    RISK_REPORT_SKILL,
    VENDOR_RESEARCH_SKILL,
)
from app.skills.registry import SkillRegistry


def create_default_skill_registry() -> SkillRegistry:
    """Create the registry containing supported application skills."""

    registry = SkillRegistry()

    registry.register(PROPOSAL_ANALYSIS_SKILL)
    registry.register(VENDOR_RESEARCH_SKILL)
    registry.register(RISK_REPORT_SKILL)

    return registry
