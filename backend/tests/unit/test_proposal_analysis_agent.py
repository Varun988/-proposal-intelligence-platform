import pytest

from app.agents.proposal_analysis.agent import (
    ProposalAnalysisAgent,
)
from app.agents.proposal_analysis.schemas import (
    FindingConfidence,
    ProposalAnalysisInput,
)
from app.core.exceptions import (
    AgentConfigurationError,
    AgentOutputValidationError,
    AgentToolLimitError,
)
from app.services.llm_service import LLMService
from app.tools.registry import ToolRegistry
from tests.fakes import FakeLLMProvider
from tests.proposal_agent_fakes import (
    FakeSearchEvidenceTool,
)


def create_structured_result() -> dict[str, object]:
    """Create valid structured LLM output."""

    return {
        "assessment_id": "assessment-001",
        "proposal_document_id": "proposal-001",
        "summary": {
            "vendor_name": None,
            "proposal_title": None,
            "scope_summary": None,
            "delivery_timeline": "Twelve months",
            "pricing_summary": None,
            "support_summary": None,
            "staffing_summary": None,
            "security_summary": None,
            "assumptions": [],
            "dependencies": [],
            "exclusions": [],
        },
        "requirement_assessments": [],
        "findings": [
            {
                "finding_id": "finding-001",
                "category": "delivery",
                "title": "Twelve-month delivery timeline",
                "description": ("The proposal states a twelve-month implementation timeline."),
                "severity": "medium",
                "confidence": "high",
                "evidence": [
                    {
                        "chunk_id": "chunk-001",
                        "document_id": "proposal-001",
                        "file_name": ("synthetic-proposal.pdf"),
                        "page_number": 4,
                        "citation_label": ("synthetic-proposal.pdf, page 4"),
                        "supporting_text": ("The implementation timeline is twelve months."),
                        "retrieval_score": 0.88,
                        "final_score": 0.92,
                    }
                ],
                "recommendation": ("Confirm alignment with the target go-live date."),
                "human_review_required": True,
            }
        ],
        "missing_information": [],
        "contradictions": [],
        "executive_summary": ("The proposal contains a twelve-month implementation timeline."),
        "overall_confidence": "high",
        "human_review_required": True,
        "analysis_limitations": [],
    }


def create_agent(
    structured_data: dict[str, object] | None = None,
    max_tool_calls: int = 15,
) -> tuple[
    ProposalAnalysisAgent,
    FakeSearchEvidenceTool,
    FakeLLMProvider,
]:
    """Create an agent using fake tools and a fake LLM."""

    search_tool = FakeSearchEvidenceTool()

    registry = ToolRegistry()
    registry.register(search_tool)

    provider = FakeLLMProvider(
        response_content="Structured analysis completed.",
        structured_data=(
            structured_data if structured_data is not None else create_structured_result()
        ),
    )

    llm_service = LLMService(
        provider=provider,
        max_calls_per_assessment=2,
    )

    agent = ProposalAnalysisAgent(
        tool_registry=registry,
        llm_service=llm_service,
        max_tool_calls=max_tool_calls,
    )

    return agent, search_tool, provider


@pytest.mark.asyncio
async def test_agent_returns_structured_analysis() -> None:
    agent, search_tool, provider = create_agent()

    execution = await agent.analyze(
        ProposalAnalysisInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            analysis_objectives=[
                "delivery timeline",
            ],
        )
    )

    assert execution.result.summary.delivery_timeline == "Twelve months"

    assert execution.result.overall_confidence is FindingConfidence.HIGH

    assert len(execution.result.findings) == 1
    assert execution.tool_call_count == 1
    assert execution.llm_provider == "fake"
    assert execution.llm_model == "fake-model"
    assert execution.instruction_version == "1.0.0"
    assert execution.total_execution_time_ms >= 0

    assert search_tool.received_queries == ["Find proposal evidence about delivery timeline."]

    assert len(provider.received_requests) == 1


@pytest.mark.asyncio
async def test_agent_records_tool_trace() -> None:
    agent, _, _ = create_agent()

    execution = await agent.analyze(
        ProposalAnalysisInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            analysis_objectives=[
                "delivery timeline",
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

    await agent.analyze(
        ProposalAnalysisInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            analysis_objectives=[
                "delivery timeline",
            ],
        )
    )

    request = provider.received_requests[0]

    assert request.temperature == 0.0
    assert request.response_schema is not None

    assert request.metadata["agent_name"] == "proposal-analysis"

    assert request.metadata["instruction_version"] == "1.0.0"

    assert request.metadata["assessment_id"] == "assessment-001"


@pytest.mark.asyncio
async def test_agent_enforces_tool_call_limit() -> None:
    agent, _, _ = create_agent(
        max_tool_calls=1,
    )

    with pytest.raises(
        AgentToolLimitError,
        match="more tool calls",
    ):
        await agent.analyze(
            ProposalAnalysisInput(
                assessment_id="assessment-001",
                proposal_document_id="proposal-001",
                analysis_objectives=[
                    "delivery timeline",
                    "pricing",
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
        ProposalAnalysisAgent(
            tool_registry=registry,
            llm_service=llm_service,
        )


@pytest.mark.asyncio
async def test_agent_rejects_missing_structured_output() -> None:
    agent, _, _ = create_agent(
        structured_data={},
    )

    with pytest.raises(
        AgentOutputValidationError,
        match="invalid structured output",
    ):
        await agent.analyze(
            ProposalAnalysisInput(
                assessment_id="assessment-001",
                proposal_document_id="proposal-001",
                analysis_objectives=[
                    "delivery timeline",
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
        await agent.analyze(
            ProposalAnalysisInput(
                assessment_id="assessment-001",
                proposal_document_id="proposal-001",
                analysis_objectives=[
                    "delivery timeline",
                ],
            )
        )


@pytest.mark.asyncio
async def test_agent_rejects_mismatched_document_id() -> None:
    structured_data = create_structured_result()
    structured_data["proposal_document_id"] = "wrong-proposal"

    agent, _, _ = create_agent(
        structured_data=structured_data,
    )

    with pytest.raises(
        AgentOutputValidationError,
        match="proposal document ID does not match",
    ):
        await agent.analyze(
            ProposalAnalysisInput(
                assessment_id="assessment-001",
                proposal_document_id="proposal-001",
                analysis_objectives=[
                    "delivery timeline",
                ],
            )
        )


def test_agent_rejects_invalid_tool_limit() -> None:
    registry = ToolRegistry()
    registry.register(FakeSearchEvidenceTool())

    llm_service = LLMService(
        provider=FakeLLMProvider(),
        max_calls_per_assessment=2,
    )

    with pytest.raises(
        AgentConfigurationError,
        match="must allow at least one tool call",
    ):
        ProposalAnalysisAgent(
            tool_registry=registry,
            llm_service=llm_service,
            max_tool_calls=0,
        )
