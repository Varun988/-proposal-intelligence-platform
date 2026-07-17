from app.agents.risk_report.instructions import (
    RISK_REPORT_INSTRUCTION_VERSION,
    RISK_REPORT_SYSTEM_INSTRUCTIONS,
)
from app.agents.risk_report.policies import (
    RISK_REPORT_AGENT_NAME,
    RISK_REPORT_ALLOWED_SOURCE_AGENTS,
    RISK_REPORT_DECISION_DISCLAIMER,
    RISK_REPORT_MAX_TOOL_CALLS,
)


def test_risk_report_has_versioned_instructions() -> None:
    assert RISK_REPORT_INSTRUCTION_VERSION == "1.0.0"
    assert RISK_REPORT_SYSTEM_INSTRUCTIONS


def test_instructions_preserve_governance() -> None:
    instructions = " ".join(RISK_REPORT_SYSTEM_INSTRUCTIONS.casefold().split())

    assert "do not calculate" in instructions
    assert "do not approve" in instructions
    assert "human review" in instructions
    assert "untrusted document content" in instructions
    assert "deterministic risk score" in instructions


def test_risk_report_has_expected_source_agents() -> None:
    assert RISK_REPORT_AGENT_NAME == "risk-report"

    assert RISK_REPORT_ALLOWED_SOURCE_AGENTS == (
        "proposal-analysis",
        "vendor-research",
    )


def test_risk_report_has_bounded_tool_calls() -> None:
    assert 1 <= RISK_REPORT_MAX_TOOL_CALLS <= 10


def test_decision_disclaimer_preserves_human_authority() -> None:
    disclaimer = RISK_REPORT_DECISION_DISCLAIMER.casefold()

    assert "decision-support" in disclaimer
    assert "authorized human reviewers" in disclaimer
    assert "approval" in disclaimer
    assert "risk acceptance" in disclaimer
