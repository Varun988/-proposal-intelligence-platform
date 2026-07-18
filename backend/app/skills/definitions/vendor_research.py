from app.agents.vendor_research.instructions import (
    VENDOR_RESEARCH_INSTRUCTION_VERSION,
)
from app.agents.vendor_research.policies import (
    VENDOR_RESEARCH_AGENT_NAME,
    VENDOR_RESEARCH_MAX_TOOL_CALLS,
)
from app.skills.schemas import SkillDefinition

VENDOR_RESEARCH_SKILL = SkillDefinition(
    name="vendor-research",
    version=VENDOR_RESEARCH_INSTRUCTION_VERSION,
    description=(
        "Collect and analyze approved vendor evidence while "
        "preserving source, date, freshness, and citation metadata."
    ),
    owning_agent=VENDOR_RESEARCH_AGENT_NAME,
    capabilities=[
        "vendor-profile-research",
        "vendor-financial-research",
        "vendor-security-research",
        "vendor-compliance-research",
        "vendor-reputation-research",
        "evidence-freshness-analysis",
        "evidence-conflict-detection",
    ],
    required_tools=[
        "search_evidence",
    ],
    optional_tools=[
        "get_document_page",
    ],
    input_schema_name="VendorResearchInput",
    output_schema_name="VendorResearchExecution",
    evaluator_names=[
        "vendor-research-citation-evaluator",
        "vendor-research-trajectory-evaluator",
    ],
    maximum_tool_calls=VENDOR_RESEARCH_MAX_TOOL_CALLS,
    human_review_required=True,
)
