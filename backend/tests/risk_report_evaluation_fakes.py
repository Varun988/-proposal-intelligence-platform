from app.agents.proposal_analysis.schemas import (
    EvidenceReference,
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
    RiskReportExecution,
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
        supporting_text=(
            "The implementation timeline is twelve months."
        ),
        retrieval_score=0.90,
        final_score=0.95,
    )


def create_risk_report_execution() -> RiskReportExecution:
    """Create a valid Risk and Report Agent execution."""

    risk = SynthesizedRisk(
        risk_id="risk-001",
        category=RiskCategory.DELIVERY,
        title="Delivery timeline requires validation",
        description=(
            "The proposal states a twelve-month timeline."
        ),
        severity=RiskSeverity.MEDIUM,
        confidence=RiskConfidence.HIGH,
        evidence=[
            RiskEvidenceReference(
                source_agent="proposal-analysis",
                source_finding_id="proposal-finding-001",
                proposal_evidence=create_proposal_evidence(),
            )
        ],
        business_impact=(
            "Timeline misalignment may delay go-live."
        ),
        mitigation=(
            "Validate milestones, dependencies, and dates."
        ),
        human_review_required=True,
    )

    result = RiskReportResult(
        assessment_id="assessment-001",
        proposal_document_id="proposal-001",
        vendor_name="Example Digital Services",
        risks=[risk],
        reviewer_report=ReviewerReport(
            title="Proposal and Vendor Risk Review",
            purpose="Support authorized specialist review.",
            sections=[
                ReportSection(
                    section_id="delivery-risk-section",
                    title="Delivery Risk",
                    content=(
                        "The proposed timeline requires validation."
                    ),
                    related_risk_ids=["risk-001"],
                    related_finding_ids=[
                        "proposal-finding-001",
                    ],
                )
            ],
            unresolved_questions=[
                "Does the timeline align with go-live?"
            ],
            required_human_actions=[
                "Validate the proposed schedule."
            ],
        ),
        executive_report=ExecutiveReport(
            title="Executive Proposal Risk Summary",
            executive_summary=(
                "A delivery timeline risk requires review."
            ),
            key_strengths=[
                "An explicit timeline is provided."
            ],
            key_risks=[
                "Timeline alignment remains unresolved."
            ],
            unresolved_decisions=[
                "Confirm the required go-live date."
            ],
            proposed_conditions=[
                "Validate the delivery schedule."
            ],
            decision_disclaimer=(
                RISK_REPORT_DECISION_DISCLAIMER
            ),
        ),
        clarification_questions=[
            "Can the vendor confirm schedule alignment?"
        ],
        overall_confidence=RiskConfidence.HIGH,
        human_review_required=True,
        official_decision_provided=False,
    )

    return RiskReportExecution(
        result=result,
        source_proposal_finding_ids=[
            "proposal-finding-001",
        ],
        source_vendor_finding_ids=[],
        llm_provider="fake",
        llm_model="fake-model",
        instruction_version="1.0.0",
        total_execution_time_ms=10.0,
    )