from app.agents.proposal_analysis.instructions import (
    PROPOSAL_ANALYSIS_INSTRUCTION_VERSION,
)
from app.agents.proposal_analysis.policies import (
    PROPOSAL_ANALYSIS_AGENT_NAME,
    PROPOSAL_ANALYSIS_ALLOWED_TOOLS,
    PROPOSAL_ANALYSIS_MAX_TOOL_CALLS,
)
from app.agents.risk_report.instructions import (
    RISK_REPORT_INSTRUCTION_VERSION,
)
from app.agents.risk_report.policies import (
    RISK_REPORT_AGENT_NAME,
    RISK_REPORT_ALLOWED_TOOLS,
    RISK_REPORT_MAX_TOOL_CALLS,
)
from app.agents.vendor_research.instructions import (
    VENDOR_RESEARCH_INSTRUCTION_VERSION,
)
from app.agents.vendor_research.policies import (
    VENDOR_RESEARCH_AGENT_NAME,
    VENDOR_RESEARCH_ALLOWED_TOOLS,
    VENDOR_RESEARCH_MAX_TOOL_CALLS,
)
from app.evaluation.proposal_analysis import (
    create_proposal_analysis_evaluation_runner,
)
from app.evaluation.risk_report import (
    create_risk_report_evaluation_runner,
)
from app.evaluation.vendor_research import (
    create_vendor_research_evaluation_runner,
)
from app.skills.factory import (
    create_default_skill_registry,
)
from app.skills.registry import SkillRegistry
from app.skills.validator import SkillRuntimeValidator


def validate_default_skill_runtime(
    skill_registry: SkillRegistry | None = None,
) -> SkillRegistry:
    """Validate and return the default skill registry."""

    registry = skill_registry if skill_registry is not None else create_default_skill_registry()

    proposal_evaluation_runner = create_proposal_analysis_evaluation_runner()
    vendor_evaluation_runner = create_vendor_research_evaluation_runner()
    risk_evaluation_runner = create_risk_report_evaluation_runner()

    validator = SkillRuntimeValidator()

    validator.validate(
        skill_registry=registry,
        allowed_tools_by_agent={
            PROPOSAL_ANALYSIS_AGENT_NAME: (PROPOSAL_ANALYSIS_ALLOWED_TOOLS),
            VENDOR_RESEARCH_AGENT_NAME: (VENDOR_RESEARCH_ALLOWED_TOOLS),
            RISK_REPORT_AGENT_NAME: (RISK_REPORT_ALLOWED_TOOLS),
        },
        evaluator_names_by_agent={
            PROPOSAL_ANALYSIS_AGENT_NAME: (proposal_evaluation_runner.evaluator_names),
            VENDOR_RESEARCH_AGENT_NAME: (vendor_evaluation_runner.evaluator_names),
            RISK_REPORT_AGENT_NAME: (risk_evaluation_runner.evaluator_names),
        },
        instruction_versions_by_agent={
            PROPOSAL_ANALYSIS_AGENT_NAME: (PROPOSAL_ANALYSIS_INSTRUCTION_VERSION),
            VENDOR_RESEARCH_AGENT_NAME: (VENDOR_RESEARCH_INSTRUCTION_VERSION),
            RISK_REPORT_AGENT_NAME: (RISK_REPORT_INSTRUCTION_VERSION),
        },
        maximum_tool_calls_by_agent={
            PROPOSAL_ANALYSIS_AGENT_NAME: (PROPOSAL_ANALYSIS_MAX_TOOL_CALLS),
            VENDOR_RESEARCH_AGENT_NAME: (VENDOR_RESEARCH_MAX_TOOL_CALLS),
            RISK_REPORT_AGENT_NAME: (RISK_REPORT_MAX_TOOL_CALLS),
        },
    )

    return registry
