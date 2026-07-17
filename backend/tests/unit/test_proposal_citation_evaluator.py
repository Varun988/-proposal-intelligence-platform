from copy import deepcopy

from app.agents.proposal_analysis.schemas import (
    AgentToolCallTrace,
    EvidenceReference,
    FindingCategory,
    FindingConfidence,
    FindingSeverity,
    ProposalAnalysisExecution,
    ProposalAnalysisResult,
    ProposalFinding,
    ProposalSummary,
)
from app.evaluation.evaluators.citation import (
    ProposalCitationEvaluator,
)
from app.evaluation.schemas import (
    EvaluationSeverity,
    EvaluationStatus,
)


def create_evidence(
    chunk_id: str = "chunk-001",
    page_number: int = 4,
) -> EvidenceReference:
    """Create synthetic evidence for evaluator tests."""

    return EvidenceReference(
        chunk_id=chunk_id,
        document_id="proposal-001",
        file_name="synthetic-proposal.pdf",
        page_number=page_number,
        citation_label=(f"synthetic-proposal.pdf, page {page_number}"),
        supporting_text=("The implementation timeline is twelve months."),
        retrieval_score=0.88,
        final_score=0.92,
    )


def create_execution() -> ProposalAnalysisExecution:
    """Create a valid proposal-analysis execution."""

    evidence = create_evidence()

    result = ProposalAnalysisResult(
        assessment_id="assessment-001",
        proposal_document_id="proposal-001",
        summary=ProposalSummary(
            delivery_timeline="Twelve months",
        ),
        findings=[
            ProposalFinding(
                finding_id="finding-001",
                category=FindingCategory.DELIVERY,
                title="Twelve-month delivery timeline",
                description=("The proposal states a twelve-month timeline."),
                severity=FindingSeverity.MEDIUM,
                confidence=FindingConfidence.HIGH,
                evidence=[evidence],
                recommendation=("Confirm alignment with the required go-live."),
            )
        ],
        executive_summary=("The proposal states a twelve-month timeline."),
        overall_confidence=FindingConfidence.HIGH,
    )

    return ProposalAnalysisExecution(
        result=result,
        retrieved_evidence=[evidence],
        tool_calls=[
            AgentToolCallTrace(
                tool_name="search_evidence",
                query="Find delivery timeline evidence.",
                succeeded=True,
                execution_time_ms=1.0,
                result_count=1,
            )
        ],
        tool_call_count=1,
        llm_provider="fake",
        llm_model="fake-model",
        instruction_version="1.0.0",
        total_execution_time_ms=10.0,
    )


def test_evaluator_passes_valid_citations() -> None:
    evaluator = ProposalCitationEvaluator()

    result = evaluator.evaluate(
        create_execution(),
    )

    assert result.status is EvaluationStatus.PASSED
    assert result.score == 1.0
    assert result.finding_count == 0
    assert result.metrics["valid_citation_count"] == 1
    assert result.metrics["invalid_citation_count"] == 0


def test_evaluator_fails_unknown_chunk_id() -> None:
    execution = create_execution()

    invalid_evidence = create_evidence(
        chunk_id="unknown-chunk",
    )

    execution.result.findings[0].evidence = [invalid_evidence]

    evaluator = ProposalCitationEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED
    assert result.score < 1.0
    assert result.critical_finding_count == 1
    assert result.metrics["invalid_citation_count"] == 1


def test_evaluator_fails_mismatched_page_number() -> None:
    execution = create_execution()

    mismatched_evidence = deepcopy(execution.result.findings[0].evidence[0])
    mismatched_evidence.page_number = 99
    mismatched_evidence.citation_label = "synthetic-proposal.pdf, page 99"

    execution.result.findings[0].evidence = [mismatched_evidence]

    evaluator = ProposalCitationEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED
    assert result.critical_finding_count == 1

    mismatches = result.findings[0].metadata["mismatched_fields"]

    assert "page_number" in mismatches
    assert "citation_label" in mismatches


def test_evaluator_reports_duplicate_citation() -> None:
    execution = create_execution()
    evidence = execution.result.findings[0].evidence[0]

    execution.result.findings[0].evidence = [
        evidence,
        deepcopy(evidence),
    ]

    evaluator = ProposalCitationEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.PASSED
    assert result.finding_count == 1
    assert result.findings[0].severity is EvaluationSeverity.LOW


def test_evaluator_allows_low_confidence_without_evidence() -> None:
    execution = create_execution()

    execution.result.findings = [
        ProposalFinding(
            finding_id="finding-002",
            category=FindingCategory.SECURITY,
            title="Certification evidence not found",
            description=("No security certification was found."),
            severity=FindingSeverity.MEDIUM,
            confidence=FindingConfidence.LOW,
            recommendation=("Request current certification evidence."),
        )
    ]

    evaluator = ProposalCitationEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.PASSED
    assert result.score == 1.0
    assert result.metrics["findings_requiring_evidence"] == 0
