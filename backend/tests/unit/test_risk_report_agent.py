import pytest

from app.agents.proposal_analysis.schemas import (
    EvidenceReference,
    FindingCategory,
    FindingConfidence,
    FindingSeverity,
    ProposalAnalysisResult,
    ProposalFinding,
    ProposalSummary,
)
from app.agents.risk_report.agent import RiskReportAgent
from app.agents.risk_report.policies import (
    RISK_REPORT_DECISION_DISCLAIMER,
)
from app.agents.risk_report.schemas import (
    RiskReportInput,
)
from app.core.exceptions import AgentOutputValidationError
from app.services.llm_service import LLMService
from tests.fakes import FakeLLMProvider


def create_proposal_evidence() -> EvidenceReference:
    """Create synthetic proposal evidence."""

    return EvidenceReference(
        chunk_id="proposal-chunk-001",
        document_id="proposal-001",
        file_name="synthetic-proposal.pdf",
        page_number=4,
        citation_label="synthetic-proposal.pdf, page 4",
        supporting_text=("The implementation timeline is twelve months."),
        retrieval_score=0.90,
        final_score=0.95,
    )


def create_proposal_result() -> ProposalAnalysisResult:
    """Create a valid Proposal Analysis result."""

    return ProposalAnalysisResult(
        assessment_id="assessment-001",
        proposal_document_id="proposal-001",
        summary=ProposalSummary(
            delivery_timeline="Twelve months",
        ),
        findings=[
            ProposalFinding(
                finding_id="proposal-finding-001",
                category=FindingCategory.DELIVERY,
                title="Twelve-month delivery timeline",
                description=("The proposal states a twelve-month implementation timeline."),
                severity=FindingSeverity.MEDIUM,
                confidence=FindingConfidence.HIGH,
                evidence=[
                    create_proposal_evidence(),
                ],
                recommendation=("Validate alignment with the target date."),
            )
        ],
        executive_summary=("The proposal contains a twelve-month timeline."),
        overall_confidence=FindingConfidence.HIGH,
    )


def create_input() -> RiskReportInput:
    """Create valid input for Risk and Report tests."""

    return RiskReportInput(
        assessment_id="assessment-001",
        proposal_document_id="proposal-001",
        vendor_name="Example Digital Services",
        proposal_analysis=create_proposal_result(),
    )


def create_structured_result() -> dict[str, object]:
    """Create valid structured Risk and Report output."""

    return {
        "assessment_id": "assessment-001",
        "proposal_document_id": "proposal-001",
        "vendor_name": "Example Digital Services",
        "risks": [
            {
                "risk_id": "risk-001",
                "category": "delivery",
                "title": "Delivery timeline requires validation",
                "description": (
                    "The proposal states a twelve-month timeline, "
                    "but alignment with the required date has not "
                    "been confirmed."
                ),
                "severity": "medium",
                "confidence": "high",
                "status": "pending_clarification",
                "evidence": [
                    {
                        "source_agent": "proposal-analysis",
                        "source_finding_id": ("proposal-finding-001"),
                        "proposal_evidence": {
                            "chunk_id": "proposal-chunk-001",
                            "document_id": "proposal-001",
                            "file_name": ("synthetic-proposal.pdf"),
                            "page_number": 4,
                            "citation_label": ("synthetic-proposal.pdf, page 4"),
                            "supporting_text": ("The implementation timeline is twelve months."),
                            "retrieval_score": 0.90,
                            "final_score": 0.95,
                        },
                        "vendor_evidence": None,
                    }
                ],
                "business_impact": ("A timeline mismatch may delay the target go-live date."),
                "mitigation": (
                    "Validate milestones, dependencies, and the required completion date."
                ),
                "clarification_question": (
                    "Can the vendor confirm alignment with the required go-live date?"
                ),
                "deterministic_score": None,
                "human_review_required": True,
            }
        ],
        "reviewer_report": {
            "title": "Proposal and Vendor Risk Review",
            "purpose": ("Support authorized specialist review."),
            "sections": [
                {
                    "section_id": "delivery-risk",
                    "title": "Delivery Risk",
                    "content": ("The twelve-month timeline requires specialist validation."),
                    "related_risk_ids": [
                        "risk-001",
                    ],
                    "related_finding_ids": [
                        "proposal-finding-001",
                    ],
                }
            ],
            "unresolved_questions": [
                ("Does the proposed timeline align with the required go-live date?")
            ],
            "required_human_actions": ["Validate the proposed delivery schedule."],
        },
        "executive_report": {
            "title": "Executive Proposal Risk Summary",
            "executive_summary": (
                "The proposal contains a twelve-month delivery "
                "timeline that requires human validation."
            ),
            "key_strengths": ["The proposal provides an explicit timeline."],
            "key_risks": ["Timeline alignment has not been confirmed."],
            "unresolved_decisions": ["Confirm the required go-live date."],
            "proposed_conditions": [
                ("Accept the schedule only after authorized specialist validation.")
            ],
            "decision_disclaimer": (RISK_REPORT_DECISION_DISCLAIMER),
        },
        "clarification_questions": [
            ("Can the vendor confirm alignment with the required go-live date?")
        ],
        "analysis_limitations": ["Vendor Research output was not supplied."],
        "overall_confidence": "high",
        "human_review_required": True,
        "official_decision_provided": False,
    }


def create_agent(
    structured_data: dict[str, object] | None = None,
) -> tuple[RiskReportAgent, FakeLLMProvider]:
    """Create an agent using a fake LLM provider."""

    provider = FakeLLMProvider(
        response_content="Risk report completed.",
        structured_data=(
            structured_data if structured_data is not None else create_structured_result()
        ),
    )

    llm_service = LLMService(
        provider=provider,
        max_calls_per_assessment=2,
    )

    return RiskReportAgent(
        llm_service=llm_service,
    ), provider


@pytest.mark.asyncio
async def test_agent_returns_structured_risk_report() -> None:
    agent, provider = create_agent()

    execution = await agent.generate_report(
        create_input(),
    )

    assert execution.result.assessment_id == "assessment-001"
    assert execution.result.vendor_name == "Example Digital Services"
    assert len(execution.result.risks) == 1
    assert execution.result.human_review_required is True
    assert execution.result.official_decision_provided is False

    assert execution.source_proposal_finding_ids == ["proposal-finding-001"]
    assert execution.source_vendor_finding_ids == []

    assert execution.llm_provider == "fake"
    assert execution.llm_model == "fake-model"
    assert execution.instruction_version == "1.0.0"
    assert execution.total_execution_time_ms >= 0
    assert len(provider.received_requests) == 1


@pytest.mark.asyncio
async def test_agent_builds_structured_llm_request() -> None:
    agent, provider = create_agent()

    await agent.generate_report(
        create_input(),
    )

    request = provider.received_requests[0]

    assert request.temperature == 0.0
    assert request.response_schema is not None

    assert request.metadata["agent_name"] == "risk-report"
    assert request.metadata["assessment_id"] == ("assessment-001")
    assert request.metadata["instruction_version"] == "1.0.0"

    user_message = request.messages[1].content

    assert "do_not_calculate_official_scores" in user_message
    assert RISK_REPORT_DECISION_DISCLAIMER in user_message


@pytest.mark.asyncio
async def test_agent_rejects_invalid_structured_output() -> None:
    agent, _ = create_agent(
        structured_data={},
    )

    with pytest.raises(
        AgentOutputValidationError,
        match="invalid structured output",
    ):
        await agent.generate_report(
            create_input(),
        )


@pytest.mark.asyncio
async def test_agent_rejects_assessment_id_mismatch() -> None:
    structured_data = create_structured_result()
    structured_data["assessment_id"] = "wrong-assessment"

    agent, _ = create_agent(
        structured_data=structured_data,
    )

    with pytest.raises(
        AgentOutputValidationError,
        match="assessment ID does not match",
    ):
        await agent.generate_report(
            create_input(),
        )


@pytest.mark.asyncio
async def test_agent_rejects_document_id_mismatch() -> None:
    structured_data = create_structured_result()
    structured_data["proposal_document_id"] = "wrong-proposal"

    agent, _ = create_agent(
        structured_data=structured_data,
    )

    with pytest.raises(
        AgentOutputValidationError,
        match="proposal document ID does not match",
    ):
        await agent.generate_report(
            create_input(),
        )


@pytest.mark.asyncio
async def test_agent_rejects_vendor_name_mismatch() -> None:
    structured_data = create_structured_result()
    structured_data["vendor_name"] = "Wrong Vendor"

    agent, _ = create_agent(
        structured_data=structured_data,
    )

    with pytest.raises(
        AgentOutputValidationError,
        match="vendor name does not match",
    ):
        await agent.generate_report(
            create_input(),
        )


@pytest.mark.asyncio
async def test_agent_canonicalizes_decision_disclaimer() -> None:
    structured_data = create_structured_result()

    executive_report = structured_data[
        "executive_report"
    ]

    assert isinstance(
        executive_report,
        dict,
    )

    executive_report["decision_disclaimer"] = (
        "Incomplete model-generated disclaimer."
    )

    agent, _ = create_agent(
        structured_data=structured_data,
    )

    execution = await agent.generate_report(
        create_input(),
    )

    assert (
        execution
        .result
        .executive_report
        .decision_disclaimer
        == RISK_REPORT_DECISION_DISCLAIMER
    )
    
@pytest.mark.asyncio
async def test_agent_rejects_unknown_source_finding() -> None:
    structured_data = create_structured_result()

    risks = structured_data["risks"]

    assert isinstance(risks, list)
    assert isinstance(risks[0], dict)

    evidence_items = risks[0]["evidence"]

    assert isinstance(evidence_items, list)
    assert isinstance(evidence_items[0], dict)

    evidence_items[0]["source_finding_id"] = "unknown-proposal-finding"

    agent, _ = create_agent(
        structured_data=structured_data,
    )

    with pytest.raises(
        AgentOutputValidationError,
        match="unknown Proposal Analysis finding",
    ):
        await agent.generate_report(
            create_input(),
        )


@pytest.mark.asyncio
async def test_agent_canonicalizes_decision_disclaimer() -> None:
    structured_data = create_structured_result()

    executive_report = structured_data["executive_report"]

    assert isinstance(executive_report, dict)

    executive_report["decision_disclaimer"] = "Human review is required."

    agent, _ = create_agent(
        structured_data=structured_data,
    )

    execution = await agent.generate_report(
        create_input(),
    )

    assert execution.result.executive_report.decision_disclaimer == RISK_REPORT_DECISION_DISCLAIMER


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_agent_alias",
    [
        "proposal_analysis",
        "proposal analysis",
        "Proposal Analysis",
        "PROPOSAL_ANALYSIS",
    ],
)
async def test_agent_normalizes_proposal_source_agent_alias(
    source_agent_alias: str,
) -> None:
    structured_data = create_structured_result()

    risks = structured_data["risks"]

    assert isinstance(risks, list)
    assert isinstance(risks[0], dict)

    evidence_items = risks[0]["evidence"]

    assert isinstance(evidence_items, list)
    assert isinstance(evidence_items[0], dict)

    evidence_items[0]["source_agent"] = source_agent_alias

    agent, _ = create_agent(
        structured_data=structured_data,
    )

    execution = await agent.generate_report(
        create_input(),
    )

    assert execution.result.risks[0].evidence[0].source_agent == "proposal-analysis"


@pytest.mark.asyncio
async def test_agent_does_not_normalize_unknown_source_agent() -> None:
    structured_data = create_structured_result()

    risks = structured_data["risks"]

    assert isinstance(risks, list)
    assert isinstance(risks[0], dict)

    evidence_items = risks[0]["evidence"]

    assert isinstance(evidence_items, list)
    assert isinstance(evidence_items[0], dict)

    evidence_items[0]["source_agent"] = "unapproved-research-agent"

    agent, _ = create_agent(
        structured_data=structured_data,
    )

    with pytest.raises(
        AgentOutputValidationError,
        match="unauthorized source agent",
    ):
        await agent.generate_report(
            create_input(),
        )


def test_agent_exposes_identity() -> None:
    agent, _ = create_agent()

    assert agent.name == "risk-report"
    assert agent.instruction_version == "1.0.0"
