from app.agents.proposal_analysis.instructions import (
    PROPOSAL_ANALYSIS_INSTRUCTION_VERSION,
)
from app.agents.proposal_analysis.policies import (
    PROPOSAL_ANALYSIS_AGENT_NAME,
    PROPOSAL_ANALYSIS_MAX_TOOL_CALLS,
)
from app.agents.risk_report.instructions import (
    RISK_REPORT_INSTRUCTION_VERSION,
)
from app.agents.risk_report.policies import (
    RISK_REPORT_AGENT_NAME,
    RISK_REPORT_MAX_TOOL_CALLS,
)
from app.agents.vendor_research.instructions import (
    VENDOR_RESEARCH_INSTRUCTION_VERSION,
)
from app.agents.vendor_research.policies import (
    VENDOR_RESEARCH_AGENT_NAME,
    VENDOR_RESEARCH_MAX_TOOL_CALLS,
)
from app.skills.definitions import (
    PROPOSAL_ANALYSIS_SKILL,
    RISK_REPORT_SKILL,
    VENDOR_RESEARCH_SKILL,
)
from app.skills.schemas import SkillStatus


def test_proposal_analysis_skill_definition() -> None:
    assert PROPOSAL_ANALYSIS_SKILL.name == "proposal-analysis"
    assert PROPOSAL_ANALYSIS_SKILL.owning_agent == PROPOSAL_ANALYSIS_AGENT_NAME
    assert PROPOSAL_ANALYSIS_SKILL.version == PROPOSAL_ANALYSIS_INSTRUCTION_VERSION
    assert PROPOSAL_ANALYSIS_SKILL.maximum_tool_calls == PROPOSAL_ANALYSIS_MAX_TOOL_CALLS
    assert PROPOSAL_ANALYSIS_SKILL.required_tools == [
        "search_evidence",
    ]
    assert "requirement-mapping" in PROPOSAL_ANALYSIS_SKILL.capabilities
    assert PROPOSAL_ANALYSIS_SKILL.status is SkillStatus.ACTIVE


def test_vendor_research_skill_definition() -> None:
    assert VENDOR_RESEARCH_SKILL.name == "vendor-research"
    assert VENDOR_RESEARCH_SKILL.owning_agent == VENDOR_RESEARCH_AGENT_NAME
    assert VENDOR_RESEARCH_SKILL.version == VENDOR_RESEARCH_INSTRUCTION_VERSION
    assert VENDOR_RESEARCH_SKILL.maximum_tool_calls == VENDOR_RESEARCH_MAX_TOOL_CALLS
    assert VENDOR_RESEARCH_SKILL.required_tools == [
        "search_evidence",
    ]
    assert "evidence-freshness-analysis" in VENDOR_RESEARCH_SKILL.capabilities


def test_risk_report_skill_definition() -> None:
    assert RISK_REPORT_SKILL.name == "risk-report"
    assert RISK_REPORT_SKILL.owning_agent == RISK_REPORT_AGENT_NAME
    assert RISK_REPORT_SKILL.version == RISK_REPORT_INSTRUCTION_VERSION
    assert RISK_REPORT_SKILL.maximum_tool_calls == RISK_REPORT_MAX_TOOL_CALLS
    assert RISK_REPORT_SKILL.required_tools == []
    assert RISK_REPORT_SKILL.depends_on_skills == [
        "proposal-analysis",
    ]
    assert "executive-report-generation" in RISK_REPORT_SKILL.capabilities


def test_all_default_skills_require_human_review() -> None:
    definitions = [
        PROPOSAL_ANALYSIS_SKILL,
        VENDOR_RESEARCH_SKILL,
        RISK_REPORT_SKILL,
    ]

    assert all(definition.human_review_required for definition in definitions)
