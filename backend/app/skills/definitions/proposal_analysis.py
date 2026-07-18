from app.agents.proposal_analysis.instructions import (
    PROPOSAL_ANALYSIS_INSTRUCTION_VERSION,
)
from app.agents.proposal_analysis.policies import (
    PROPOSAL_ANALYSIS_AGENT_NAME,
    PROPOSAL_ANALYSIS_MAX_TOOL_CALLS,
)
from app.skills.schemas import SkillDefinition

PROPOSAL_ANALYSIS_SKILL = SkillDefinition(
    name="proposal-analysis",
    version=PROPOSAL_ANALYSIS_INSTRUCTION_VERSION,
    description=(
        "Analyze proposal and RFP evidence and produce structured, evidence-grounded findings."
    ),
    owning_agent=PROPOSAL_ANALYSIS_AGENT_NAME,
    capabilities=[
        "proposal-summary",
        "requirement-mapping",
        "missing-information-detection",
        "contradiction-detection",
        "proposal-finding-generation",
    ],
    required_tools=[
        "search_evidence",
    ],
    optional_tools=[
        "get_document_page",
        "extract_document",
        "chunk_document",
        "index_document",
    ],
    input_schema_name="ProposalAnalysisInput",
    output_schema_name="ProposalAnalysisExecution",
    evaluator_names=[
        "proposal-citation-evaluator",
        "proposal-trajectory-evaluator",
    ],
    maximum_tool_calls=PROPOSAL_ANALYSIS_MAX_TOOL_CALLS,
    human_review_required=True,
)
