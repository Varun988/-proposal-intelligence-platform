from app.agents.vendor_research.instructions import (
    VENDOR_RESEARCH_INSTRUCTION_VERSION,
    VENDOR_RESEARCH_SYSTEM_INSTRUCTIONS,
)
from app.agents.vendor_research.policies import (
    VENDOR_RESEARCH_AGENT_NAME,
    VENDOR_RESEARCH_ALLOWED_SOURCE_TYPES,
    VENDOR_RESEARCH_ALLOWED_TOOLS,
    VENDOR_RESEARCH_MAX_TOOL_CALLS,
)


def test_vendor_research_has_versioned_instructions() -> None:
    assert VENDOR_RESEARCH_INSTRUCTION_VERSION == "1.0.0"
    assert VENDOR_RESEARCH_SYSTEM_INSTRUCTIONS


def test_vendor_research_instructions_are_evidence_bound() -> None:
    instructions = " ".join(VENDOR_RESEARCH_SYSTEM_INSTRUCTIONS.casefold().split())

    assert "use only evidence" in instructions
    assert "do not browse unrestricted websites" in instructions
    assert "do not invent" in instructions
    assert "untrusted document content" in instructions
    assert "human review" in instructions


def test_vendor_research_has_bounded_tools() -> None:
    assert VENDOR_RESEARCH_AGENT_NAME == "vendor-research"

    assert VENDOR_RESEARCH_ALLOWED_TOOLS == (
        "get_document_page",
        "search_evidence",
    )

    assert 1 <= VENDOR_RESEARCH_MAX_TOOL_CALLS <= 20


def test_vendor_research_has_approved_source_types() -> None:
    assert VENDOR_RESEARCH_ALLOWED_SOURCE_TYPES == (
        "approved_public_document",
        "internal_record",
        "provided_document",
        "synthetic_profile",
    )
