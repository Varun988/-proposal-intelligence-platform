import pytest
from pydantic import ValidationError

from app.agents.proposal_analysis.schemas import (
    EvidenceReference,
    FindingCategory,
    FindingConfidence,
    FindingSeverity,
    ProposalAnalysisInput,
    ProposalAnalysisResult,
    ProposalFinding,
    ProposalSummary,
)


def create_evidence() -> EvidenceReference:
    """Create synthetic evidence for proposal-analysis tests."""

    return EvidenceReference(
        chunk_id="chunk-001",
        document_id="proposal-001",
        file_name="synthetic-proposal.pdf",
        page_number=4,
        citation_label="synthetic-proposal.pdf, page 4",
        supporting_text=("The implementation timeline is twelve months."),
        retrieval_score=0.88,
        final_score=0.92,
    )


def test_analysis_input_has_default_objectives() -> None:
    analysis_input = ProposalAnalysisInput(
        assessment_id="assessment-001",
        proposal_document_id="proposal-001",
    )

    assert "scope" in analysis_input.analysis_objectives
    assert "delivery timeline" in analysis_input.analysis_objectives
    assert analysis_input.requirements == []


def test_high_confidence_finding_requires_evidence() -> None:
    with pytest.raises(
        ValidationError,
        match="must include supporting evidence",
    ):
        ProposalFinding(
            finding_id="finding-001",
            category=FindingCategory.DELIVERY,
            title="Delivery timeline exceeds requirement",
            description=("The proposal states a twelve-month timeline."),
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            recommendation=("Request a revised implementation schedule."),
        )


def test_medium_confidence_finding_requires_evidence() -> None:
    with pytest.raises(
        ValidationError,
        match="must include supporting evidence",
    ):
        ProposalFinding(
            finding_id="finding-001",
            category=FindingCategory.COMMERCIAL,
            title="Pricing structure may be incomplete",
            description=("The proposal may not contain all recurring costs."),
            severity=FindingSeverity.MEDIUM,
            confidence=FindingConfidence.MEDIUM,
            recommendation=("Request a complete pricing breakdown."),
        )


def test_low_confidence_finding_can_record_missing_evidence() -> None:
    finding = ProposalFinding(
        finding_id="finding-001",
        category=FindingCategory.SECURITY,
        title="Security certification not found",
        description=("No certification evidence was found in the retrieved proposal content."),
        severity=FindingSeverity.MEDIUM,
        confidence=FindingConfidence.LOW,
        recommendation=("Request current security certification evidence."),
    )

    assert finding.evidence == []
    assert finding.human_review_required is True


def test_evidence_grounded_finding_is_valid() -> None:
    finding = ProposalFinding(
        finding_id="finding-001",
        category=FindingCategory.DELIVERY,
        title="Twelve-month delivery timeline",
        description=("The proposal commits to a twelve-month implementation timeline."),
        severity=FindingSeverity.MEDIUM,
        confidence=FindingConfidence.HIGH,
        evidence=[create_evidence()],
        recommendation=("Validate alignment with the required go-live date."),
    )

    assert finding.evidence[0].page_number == 4
    assert finding.evidence[0].chunk_id == "chunk-001"
    assert finding.confidence is FindingConfidence.HIGH


def test_evidence_reference_preserves_citation_data() -> None:
    evidence = create_evidence()

    assert evidence.document_id == "proposal-001"
    assert evidence.file_name == "synthetic-proposal.pdf"
    assert evidence.page_number == 4
    assert evidence.citation_label == ("synthetic-proposal.pdf, page 4")
    assert evidence.retrieval_score == 0.88
    assert evidence.final_score == 0.92


def test_analysis_result_requires_executive_summary() -> None:
    with pytest.raises(ValidationError):
        ProposalAnalysisResult(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            summary=ProposalSummary(),
            executive_summary="",
            overall_confidence=FindingConfidence.MEDIUM,
        )


def test_analysis_result_accepts_structured_output() -> None:
    result = ProposalAnalysisResult(
        assessment_id="assessment-001",
        proposal_document_id="proposal-001",
        summary=ProposalSummary(
            delivery_timeline="Twelve months",
            support_summary="Three years after go-live",
        ),
        findings=[
            ProposalFinding(
                finding_id="finding-001",
                category=FindingCategory.DELIVERY,
                title="Twelve-month delivery timeline",
                description=("The proposal states a twelve-month timeline."),
                severity=FindingSeverity.MEDIUM,
                confidence=FindingConfidence.HIGH,
                evidence=[create_evidence()],
                recommendation=("Confirm alignment with the target go-live."),
            )
        ],
        executive_summary=(
            "The proposal contains a twelve-month delivery timeline and requires human validation."
        ),
        overall_confidence=FindingConfidence.HIGH,
    )

    assert result.assessment_id == "assessment-001"
    assert result.proposal_document_id == "proposal-001"
    assert result.summary.delivery_timeline == "Twelve months"
    assert len(result.findings) == 1
    assert result.human_review_required is True


def test_analysis_result_uses_empty_collections_by_default() -> None:
    result = ProposalAnalysisResult(
        assessment_id="assessment-001",
        proposal_document_id="proposal-001",
        summary=ProposalSummary(),
        executive_summary=(
            "Insufficient proposal evidence is available for a complete assessment."
        ),
        overall_confidence=FindingConfidence.LOW,
    )

    assert result.requirement_assessments == []
    assert result.findings == []
    assert result.missing_information == []
    assert result.contradictions == []
    assert result.analysis_limitations == []
