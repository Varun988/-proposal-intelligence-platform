from app.agents.orchestrator.instructions import (
    ORCHESTRATOR_INSTRUCTION_VERSION,
    ORCHESTRATOR_SYSTEM_INSTRUCTIONS,
)
from app.agents.orchestrator.policies import (
    ORCHESTRATOR_ALLOWED_SPECIALIST_AGENTS,
    ORCHESTRATOR_MAXIMUM_STEPS,
    ORCHESTRATOR_MAXIMUM_TASKS,
)


def test_orchestrator_has_versioned_instructions() -> None:
    assert ORCHESTRATOR_INSTRUCTION_VERSION == "1.0.0"
    assert ORCHESTRATOR_SYSTEM_INSTRUCTIONS


def test_orchestrator_instructions_preserve_governance() -> None:
    instructions = " ".join(ORCHESTRATOR_SYSTEM_INSTRUCTIONS.casefold().split())

    assert "do not approve or reject a vendor" in instructions
    assert "human review" in instructions
    assert "evaluation release gates" in instructions
    assert "specialist analysis yourself" in instructions


def test_orchestrator_has_mvp_agent_allowlist() -> None:
    assert ORCHESTRATOR_ALLOWED_SPECIALIST_AGENTS == (
        "proposal-analysis",
        "risk-report",
        "vendor-research",
    )


def test_orchestrator_limits_are_bounded() -> None:
    assert ORCHESTRATOR_MAXIMUM_TASKS == 3
    assert 1 <= ORCHESTRATOR_MAXIMUM_STEPS <= 50
