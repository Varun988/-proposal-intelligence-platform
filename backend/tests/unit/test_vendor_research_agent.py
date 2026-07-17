from datetime import date

import pytest

from app.agents.vendor_research.agent import (
    VendorResearchAgent,
)
from app.agents.vendor_research.schemas import (
    VendorEvidenceFreshness,
    VendorFindingConfidence,
    VendorResearchInput,
)
from app.core.exceptions import (
    AgentConfigurationError,
    AgentOutputValidationError,
    AgentToolLimitError,
)
from app.services.llm_service import LLMService
from app.tools.registry import ToolRegistry
from tests.fakes import FakeLLMProvider
from tests.vendor_research_fakes import (
    FakeVendorSearchTool,
)


def create_structured_result() -> dict[str, object]:
    """Create valid structured vendor-research output."""

    return {
        "assessment_id": "assessment-001",
        "vendor_name": "Example Digital Services",
        "profile": {
            "vendor_name": "Example Digital Services",
            "legal_name": None,
            "headquarters": None,
            "ownership_summary": None,
            "financial_summary": None,
            "security_summary": None,
            "compliance_summary": None,
            "reputation_summary": None,
            "confirmed_facts": [
                ("The supplied synthetic profile states that the vendor was established in 2012.")
            ],
            "vendor_claims": [],
            "unavailable_information": [],
        },
        "findings": [
            {
                "finding_id": "vendor-finding-001",
                "category": "company_profile",
                "title": "Vendor establishment date identified",
                "description": (
                    "The supplied synthetic profile states that the vendor was established in 2012."
                ),
                "severity": "low",
                "confidence": "high",
                "evidence": [
                    {
                        "evidence_id": ("evidence-vendor-profile-chunk"),
                        "chunk_id": "vendor-profile-chunk",
                        "document_id": "vendor-profile-001",
                        "file_name": ("synthetic-vendor-profile.pdf"),
                        "page_number": 2,
                        "citation_label": ("synthetic-vendor-profile.pdf, page 2"),
                        "supporting_text": ("Example Digital Services was established in 2012."),
                        "category": "company_profile",
                        "source_type": "synthetic_profile",
                        "source_name": ("Synthetic Vendor Profile"),
                        "publication_date": "2026-01-01",
                        "retrieved_date": "2026-07-17",
                        "freshness": "current",
                        "retrieval_score": 0.90,
                        "final_score": 0.95,
                        "metadata": {},
                    }
                ],
                "recommendation": (
                    "Validate the establishment date through "
                    "an approved registry before production use."
                ),
                "clarification_question": None,
                "human_review_required": True,
            }
        ],
        "conflicts": [],
        "stale_evidence_ids": [],
        "unavailable_information": [],
        "clarification_questions": [],
        "executive_summary": (
            "The supplied synthetic vendor profile was reviewed and requires human verification."
        ),
        "overall_confidence": "high",
        "human_review_required": True,
        "research_limitations": ["Only synthetic evidence was available."],
    }


def create_agent(
    structured_data: dict[str, object] | None = None,
    max_tool_calls: int = 10,
) -> tuple[
    VendorResearchAgent,
    FakeVendorSearchTool,
    FakeLLMProvider,
]:
    """Create an agent using fake tools and a fake LLM."""

    search_tool = FakeVendorSearchTool()

    registry = ToolRegistry()
    registry.register(search_tool)

    provider = FakeLLMProvider(
        response_content="Vendor research completed.",
        structured_data=(
            structured_data if structured_data is not None else create_structured_result()
        ),
    )

    llm_service = LLMService(
        provider=provider,
        max_calls_per_assessment=2,
    )

    agent = VendorResearchAgent(
        tool_registry=registry,
        llm_service=llm_service,
        max_tool_calls=max_tool_calls,
        current_date=date(2026, 7, 17),
    )

    return agent, search_tool, provider


@pytest.mark.asyncio
async def test_agent_returns_structured_vendor_research() -> None:
    agent, search_tool, provider = create_agent()

    execution = await agent.research(
        VendorResearchInput(
            assessment_id="assessment-001",
            vendor_name="Example Digital Services",
            research_objectives=[
                "company profile and ownership",
            ],
        )
    )

    assert execution.result.vendor_name == "Example Digital Services"
    assert execution.result.overall_confidence is VendorFindingConfidence.HIGH
    assert len(execution.result.findings) == 1
    assert execution.tool_call_count == 1
    assert execution.llm_provider == "fake"
    assert execution.llm_model == "fake-model"
    assert execution.instruction_version == "1.0.0"
    assert execution.total_execution_time_ms >= 0

    assert len(execution.retrieved_evidence) == 1
    assert execution.retrieved_evidence[0].freshness is VendorEvidenceFreshness.CURRENT

    assert search_tool.received_queries == [
        (
            "Find approved evidence about company profile "
            "and ownership for vendor "
            "Example Digital Services."
        )
    ]

    assert len(provider.received_requests) == 1


@pytest.mark.asyncio
async def test_agent_records_tool_trace() -> None:
    agent, _, _ = create_agent()

    execution = await agent.research(
        VendorResearchInput(
            assessment_id="assessment-001",
            vendor_name="Example Digital Services",
            research_objectives=[
                "company profile",
            ],
        )
    )

    trace = execution.tool_calls[0]

    assert trace.tool_name == "search_evidence"
    assert trace.succeeded is True
    assert trace.result_count == 1
    assert trace.execution_time_ms >= 0


@pytest.mark.asyncio
async def test_agent_builds_structured_llm_request() -> None:
    agent, _, provider = create_agent()

    await agent.research(
        VendorResearchInput(
            assessment_id="assessment-001",
            vendor_name="Example Digital Services",
            research_objectives=[
                "company profile",
            ],
        )
    )

    request = provider.received_requests[0]

    assert request.temperature == 0.0
    assert request.response_schema is not None
    assert request.metadata["agent_name"] == "vendor-research"
    assert request.metadata["instruction_version"] == "1.0.0"


@pytest.mark.asyncio
async def test_agent_enforces_tool_call_limit() -> None:
    agent, _, _ = create_agent(
        max_tool_calls=1,
    )

    with pytest.raises(
        AgentToolLimitError,
        match="more tool calls",
    ):
        await agent.research(
            VendorResearchInput(
                assessment_id="assessment-001",
                vendor_name="Example Digital Services",
                research_objectives=[
                    "company profile",
                    "financial information",
                ],
            )
        )


def test_agent_requires_search_evidence_tool() -> None:
    registry = ToolRegistry()

    llm_service = LLMService(
        provider=FakeLLMProvider(),
        max_calls_per_assessment=2,
    )

    with pytest.raises(
        AgentConfigurationError,
        match="missing required tools",
    ):
        VendorResearchAgent(
            tool_registry=registry,
            llm_service=llm_service,
        )


@pytest.mark.asyncio
async def test_agent_rejects_invalid_structured_output() -> None:
    agent, _, _ = create_agent(
        structured_data={},
    )

    with pytest.raises(
        AgentOutputValidationError,
        match="invalid structured output",
    ):
        await agent.research(
            VendorResearchInput(
                assessment_id="assessment-001",
                vendor_name="Example Digital Services",
                research_objectives=[
                    "company profile",
                ],
            )
        )


@pytest.mark.asyncio
async def test_agent_rejects_mismatched_assessment_id() -> None:
    structured_data = create_structured_result()
    structured_data["assessment_id"] = "wrong-assessment"

    agent, _, _ = create_agent(
        structured_data=structured_data,
    )

    with pytest.raises(
        AgentOutputValidationError,
        match="assessment ID does not match",
    ):
        await agent.research(
            VendorResearchInput(
                assessment_id="assessment-001",
                vendor_name="Example Digital Services",
                research_objectives=[
                    "company profile",
                ],
            )
        )


@pytest.mark.asyncio
async def test_agent_rejects_mismatched_vendor_name() -> None:
    structured_data = create_structured_result()
    structured_data["vendor_name"] = "Wrong Vendor"

    agent, _, _ = create_agent(
        structured_data=structured_data,
    )

    with pytest.raises(
        AgentOutputValidationError,
        match="vendor name does not match",
    ):
        await agent.research(
            VendorResearchInput(
                assessment_id="assessment-001",
                vendor_name="Example Digital Services",
                research_objectives=[
                    "company profile",
                ],
            )
        )


@pytest.mark.asyncio
async def test_agent_canonicalizes_evidence_metadata() -> None:
    structured_data = create_structured_result()

    findings = structured_data["findings"]

    assert isinstance(findings, list)
    assert isinstance(findings[0], dict)

    evidence_items = findings[0]["evidence"]

    assert isinstance(evidence_items, list)
    assert isinstance(evidence_items[0], dict)

    evidence_items[0]["publication_date"] = None
    evidence_items[0]["retrieved_date"] = None
    evidence_items[0]["freshness"] = "unknown"
    evidence_items[0]["retrieval_score"] = None
    evidence_items[0]["final_score"] = None
    evidence_items[0]["metadata"] = {}

    agent, _, _ = create_agent(
        structured_data=structured_data,
    )

    execution = await agent.research(
        VendorResearchInput(
            assessment_id="assessment-001",
            vendor_name="Example Digital Services",
            research_objectives=[
                "company profile",
            ],
        )
    )

    evidence = execution.result.findings[0].evidence[0]
    inventory_evidence = execution.retrieved_evidence[0]

    assert evidence == inventory_evidence
    assert evidence.publication_date == date(2026, 1, 1)
    assert evidence.retrieved_date == date(2026, 7, 17)
    assert evidence.freshness is VendorEvidenceFreshness.CURRENT
    assert evidence.retrieval_score == 0.90
    assert evidence.final_score == 0.95


@pytest.mark.asyncio
async def test_agent_does_not_canonicalize_unknown_evidence() -> None:
    structured_data = create_structured_result()

    findings = structured_data["findings"]

    assert isinstance(findings, list)
    assert isinstance(findings[0], dict)

    evidence_items = findings[0]["evidence"]

    assert isinstance(evidence_items, list)
    assert isinstance(evidence_items[0], dict)

    evidence_items[0]["evidence_id"] = "fabricated-evidence"
    evidence_items[0]["chunk_id"] = "fabricated-chunk"

    agent, _, _ = create_agent(
        structured_data=structured_data,
    )

    execution = await agent.research(
        VendorResearchInput(
            assessment_id="assessment-001",
            vendor_name="Example Digital Services",
            research_objectives=[
                "company profile",
            ],
        )
    )

    cited_evidence = execution.result.findings[0].evidence[0]

    assert cited_evidence.evidence_id == ("fabricated-evidence")
    assert cited_evidence.chunk_id == "fabricated-chunk"
