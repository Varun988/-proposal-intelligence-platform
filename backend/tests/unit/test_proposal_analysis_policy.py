from app.agents.proposal_analysis.instructions import (
    PROPOSAL_ANALYSIS_INSTRUCTION_VERSION,
    PROPOSAL_ANALYSIS_SYSTEM_INSTRUCTIONS,
)
from app.agents.proposal_analysis.policies import (
    PROPOSAL_ANALYSIS_AGENT_NAME,
    PROPOSAL_ANALYSIS_ALLOWED_TOOLS,
    PROPOSAL_ANALYSIS_MAX_TOOL_CALLS,
)


def test_agent_has_versioned_instructions() -> None:
    assert PROPOSAL_ANALYSIS_INSTRUCTION_VERSION == "1.0.0"
    assert PROPOSAL_ANALYSIS_SYSTEM_INSTRUCTIONS


def test_instructions_require_grounded_evidence() -> None:
    instructions = " ".join(PROPOSAL_ANALYSIS_SYSTEM_INSTRUCTIONS.casefold().split())

    assert "use only evidence" in instructions
    assert "do not invent" in instructions
    assert "human review" in instructions
    assert "untrusted document content" in instructions


def test_agent_has_expected_tool_allowlist() -> None:
    assert PROPOSAL_ANALYSIS_AGENT_NAME == ("proposal-analysis")

    assert PROPOSAL_ANALYSIS_ALLOWED_TOOLS == (
        "chunk_document",
        "extract_document",
        "get_document_page",
        "index_document",
        "search_evidence",
    )


def test_agent_tool_limit_is_bounded() -> None:
    assert 1 <= PROPOSAL_ANALYSIS_MAX_TOOL_CALLS <= 20
