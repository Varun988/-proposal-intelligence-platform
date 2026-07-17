import pytest
from pydantic import ValidationError

from app.agents.proposal_analysis.schemas import (
    EvidenceReference,
    FindingCategory,
    FindingConfidence,
    FindingSeverity,
    ProposalAnalysisResult,
    ProposalFinding,
    ProposalSummary,
)
from app.agents.risk_report.policies import (
    RISK_REPORT_DECISION_DISCLAIMER,
)
from app.agents.risk_report.schemas import (
    ExecutiveReport,
    ReportSection,
    ReviewerReport,
    RiskCategory,
    RiskConfidence,
    RiskEvidenceReference,
    RiskReportInput,
    RiskReportResult,
    RiskSeverity,
    SynthesizedRisk,
)


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
                evidence=[create_proposal_evidence()],
                recommendation=("Validate alignment with the required date."),
            )
        ],
        executive_summary=("The proposal contains a twelve-month timeline."),
        overall_confidence=FindingConfidence.HIGH,
    )


def create_reviewer_report() -> ReviewerReport:
    """Create a valid reviewer report."""

    return ReviewerReport(
        title="Proposal and Vendor Risk Review",
        purpose=("Support authorized specialist and management review."),
        sections=[
            ReportSection(
                section_id="delivery-risk",
                title="Delivery Risk",
                content=("The proposal states a twelve-month timeline."),
                related_risk_ids=["risk-001"],
                related_finding_ids=[
                    "proposal-finding-001",
                ],
            )
        ],
        required_human_actions=["Confirm alignment with the target go-live date."],
    )


def create_executive_report() -> ExecutiveReport:
    """Create a valid executive report."""

    return ExecutiveReport(
        title="Executive Proposal Risk Summary",
        executive_summary=(
            "The proposal contains delivery commitments requiring human validation."
        ),
        key_strengths=["A delivery timeline is explicitly stated."],
        key_risks=["Timeline alignment has not been confirmed."],
        unresolved_decisions=["Confirm the required go-live date."],
        proposed_conditions=["Approve the schedule only after specialist review."],
        decision_disclaimer=(RISK_REPORT_DECISION_DISCLAIMER),
    )


def test_risk_input_accepts_valid_specialist_output() -> None:
    risk_input = RiskReportInput(
        assessment_id="assessment-001",
        proposal_document_id="proposal-001",
        vendor_name="Example Digital Services",
        proposal_analysis=create_proposal_result(),
    )

    assert risk_input.assessment_id == "assessment-001"
    assert risk_input.vendor_research is None
    assert risk_input.human_review_required is True


def test_risk_input_rejects_assessment_mismatch() -> None:
    proposal_result = create_proposal_result()
    proposal_result.assessment_id = "wrong-assessment"

    with pytest.raises(
        ValidationError,
        match="assessment ID must match",
    ):
        RiskReportInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            vendor_name="Example Digital Services",
            proposal_analysis=proposal_result,
        )


def test_risk_input_rejects_document_mismatch() -> None:
    proposal_result = create_proposal_result()
    proposal_result.proposal_document_id = "wrong-proposal"

    with pytest.raises(
        ValidationError,
        match="document ID must match",
    ):
        RiskReportInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            vendor_name="Example Digital Services",
            proposal_analysis=proposal_result,
        )


def test_high_confidence_risk_requires_evidence() -> None:
    with pytest.raises(
        ValidationError,
        match="must include supporting evidence",
    ):
        SynthesizedRisk(
            risk_id="risk-001",
            category=RiskCategory.DELIVERY,
            title="Delivery timeline risk",
            description=("The proposed timeline may not meet the target date."),
            severity=RiskSeverity.HIGH,
            confidence=RiskConfidence.HIGH,
            business_impact=("The target go-live date may be delayed."),
            mitigation=("Validate milestones and schedule dependencies."),
        )


def test_risk_evidence_requires_exactly_one_source() -> None:
    with pytest.raises(
        ValidationError,
        match="exactly one",
    ):
        RiskEvidenceReference(
            source_agent="proposal-analysis",
            source_finding_id="proposal-finding-001",
        )


def test_risk_result_rejects_official_decision() -> None:
    with pytest.raises(
        ValidationError,
        match="cannot provide an official vendor decision",
    ):
        RiskReportResult(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            vendor_name="Example Digital Services",
            reviewer_report=create_reviewer_report(),
            executive_report=create_executive_report(),
            executive_summary="",
            overall_confidence=RiskConfidence.MEDIUM,
            official_decision_provided=True,
        )


def test_risk_result_requires_human_review() -> None:
    with pytest.raises(
        ValidationError,
        match="must require human review",
    ):
        RiskReportResult(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            vendor_name="Example Digital Services",
            reviewer_report=create_reviewer_report(),
            executive_report=create_executive_report(),
            overall_confidence=RiskConfidence.MEDIUM,
            human_review_required=False,
        )


def test_risk_result_accepts_safe_output() -> None:
    evidence = RiskEvidenceReference(
        source_agent="proposal-analysis",
        source_finding_id="proposal-finding-001",
        proposal_evidence=create_proposal_evidence(),
    )

    result = RiskReportResult(
        assessment_id="assessment-001",
        proposal_document_id="proposal-001",
        vendor_name="Example Digital Services",
        risks=[
            SynthesizedRisk(
                risk_id="risk-001",
                category=RiskCategory.DELIVERY,
                title="Delivery timeline requires validation",
                description=("The proposal states a twelve-month timeline."),
                severity=RiskSeverity.MEDIUM,
                confidence=RiskConfidence.HIGH,
                evidence=[evidence],
                business_impact=("The timeline may not align with the target."),
                mitigation=("Confirm milestones and dependencies."),
            )
        ],
        reviewer_report=create_reviewer_report(),
        executive_report=create_executive_report(),
        overall_confidence=RiskConfidence.HIGH,
    )

    assert len(result.risks) == 1
    assert result.human_review_required is True
    assert result.official_decision_provided is False
