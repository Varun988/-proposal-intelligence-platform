from app.agents.proposal_analysis.schemas import (
    AgentToolCallTrace,
    EvidenceReference,
    FindingCategory,
    FindingConfidence,
    FindingSeverity,
    ProposalAnalysisExecution,
    ProposalAnalysisInput,
    ProposalAnalysisResult,
    ProposalFinding,
    ProposalSummary,
)
from datetime import date

from app.agents.vendor_research.schemas import (
    VendorEvidenceCategory,
    VendorEvidenceFreshness,
    VendorEvidenceReference,
    VendorEvidenceSourceType,
    VendorFindingConfidence,
    VendorFindingSeverity,
    VendorProfileSummary,
    VendorResearchExecution,
    VendorResearchFinding,
    VendorResearchInput,
    VendorResearchResult,
    VendorResearchToolCallTrace,
)
from app.agents.risk_report.policies import RISK_REPORT_DECISION_DISCLAIMER
from app.agents.risk_report.schemas import (
    ExecutiveReport,
    ReportSection,
    ReviewerReport,
    RiskCategory,
    RiskConfidence,
    RiskEvidenceReference,
    RiskReportExecution,
    RiskReportInput,
    RiskReportResult,
    RiskSeverity,
    SynthesizedRisk,
)


def create_fake_proposal_result(
    assessment_id: str = "assessment-001",
    proposal_document_id: str = "proposal-001",
) -> ProposalAnalysisResult:
    """Create a reusable fake Proposal Analysis result."""

    evidence = EvidenceReference(
        chunk_id="chunk-001",
        document_id=proposal_document_id,
        file_name="synthetic-proposal.pdf",
        page_number=4,
        citation_label="synthetic-proposal.pdf, page 4",
        supporting_text=("The implementation timeline is twelve months."),
        retrieval_score=0.90,
        final_score=0.95,
    )

    return ProposalAnalysisResult(
        assessment_id=assessment_id,
        proposal_document_id=proposal_document_id,
        summary=ProposalSummary(
            delivery_timeline="Twelve months",
        ),
        findings=[
            ProposalFinding(
                finding_id="finding-001",
                category=FindingCategory.DELIVERY,
                title="Twelve-month delivery timeline",
                description=("The proposal states a twelve-month implementation timeline."),
                severity=FindingSeverity.MEDIUM,
                confidence=FindingConfidence.HIGH,
                evidence=[
                    evidence.model_copy(deep=True),
                ],
                recommendation=("Confirm alignment with the target date."),
                human_review_required=True,
            )
        ],
        executive_summary=("The proposal contains a twelve-month timeline."),
        overall_confidence=FindingConfidence.HIGH,
        human_review_required=True,
    )


class FakeProposalAnalysisAgent:
    """Deterministic Proposal Analysis Agent for workflow tests."""

    def __init__(
        self,
        should_fail: bool = False,
        disable_human_review: bool = False,
    ) -> None:
        self.should_fail = should_fail
        self.disable_human_review = disable_human_review
        self.received_inputs: list[ProposalAnalysisInput] = []

    async def analyze(
        self,
        analysis_input: ProposalAnalysisInput,
    ) -> ProposalAnalysisExecution:
        """Return a deterministic proposal-analysis execution."""

        self.received_inputs.append(
            analysis_input,
        )

        if self.should_fail:
            raise RuntimeError("Synthetic Proposal Analysis Agent failure.")

        evidence = EvidenceReference(
            chunk_id="chunk-001",
            document_id=analysis_input.proposal_document_id,
            file_name="synthetic-proposal.pdf",
            page_number=4,
            citation_label="synthetic-proposal.pdf, page 4",
            supporting_text=("The implementation timeline is twelve months."),
            retrieval_score=0.90,
            final_score=0.95,
        )

        result = ProposalAnalysisResult(
            assessment_id=analysis_input.assessment_id,
            proposal_document_id=(analysis_input.proposal_document_id),
            summary=ProposalSummary(
                delivery_timeline="Twelve months",
            ),
            findings=[
                ProposalFinding(
                    finding_id="finding-001",
                    category=FindingCategory.DELIVERY,
                    title="Twelve-month delivery timeline",
                    description=("The proposal states a twelve-month delivery timeline."),
                    severity=FindingSeverity.MEDIUM,
                    confidence=FindingConfidence.HIGH,
                    evidence=[
                        evidence.model_copy(deep=True),
                    ],
                    recommendation=("Confirm alignment with the target go-live date."),
                    human_review_required=(not self.disable_human_review),
                )
            ],
            executive_summary=("The proposal contains a twelve-month delivery timeline."),
            overall_confidence=FindingConfidence.HIGH,
            human_review_required=(not self.disable_human_review),
        )

        return ProposalAnalysisExecution(
            result=result,
            retrieved_evidence=[
                evidence.model_copy(deep=True),
            ],
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


class FakeVendorResearchAgent:
    """Deterministic Vendor Research Agent for workflow tests."""

    def __init__(
        self,
        should_fail: bool = False,
        disable_human_review: bool = False,
    ) -> None:
        self.should_fail = should_fail
        self.disable_human_review = disable_human_review
        self.received_inputs: list[VendorResearchInput] = []

    async def research(
        self,
        research_input: VendorResearchInput,
    ) -> VendorResearchExecution:
        """Return deterministic synthetic vendor research."""

        self.received_inputs.append(research_input)

        if self.should_fail:
            raise RuntimeError("Synthetic Vendor Research Agent failure.")

        evidence = VendorEvidenceReference(
            evidence_id="evidence-vendor-profile",
            chunk_id="vendor-profile",
            document_id="vendor-document-001",
            file_name="synthetic-vendor-profile.pdf",
            page_number=2,
            citation_label=("synthetic-vendor-profile.pdf, page 2"),
            supporting_text=("Example Digital Services was established in 2012."),
            category=(VendorEvidenceCategory.COMPANY_PROFILE),
            source_type=(VendorEvidenceSourceType.SYNTHETIC_PROFILE),
            source_name="Synthetic Vendor Profile",
            publication_date=date(2026, 1, 1),
            retrieved_date=date(2026, 7, 17),
            freshness=VendorEvidenceFreshness.CURRENT,
            retrieval_score=0.90,
            final_score=0.95,
        )

        result = VendorResearchResult(
            assessment_id=research_input.assessment_id,
            vendor_name=research_input.vendor_name,
            profile=VendorProfileSummary(
                vendor_name=research_input.vendor_name,
                confirmed_facts=[
                    ("The synthetic profile states that the vendor was established in 2012.")
                ],
            ),
            findings=[
                VendorResearchFinding(
                    finding_id="vendor-finding-001",
                    category=(VendorEvidenceCategory.COMPANY_PROFILE),
                    title=("Vendor establishment date identified"),
                    description=(
                        "The synthetic profile states that the vendor was established in 2012."
                    ),
                    severity=VendorFindingSeverity.LOW,
                    confidence=VendorFindingConfidence.HIGH,
                    evidence=[
                        evidence.model_copy(deep=True),
                    ],
                    recommendation=("Validate the information through an approved registry."),
                    human_review_required=(not self.disable_human_review),
                )
            ],
            executive_summary=("Synthetic vendor evidence was reviewed."),
            overall_confidence=VendorFindingConfidence.HIGH,
            human_review_required=(not self.disable_human_review),
        )

        return VendorResearchExecution(
            result=result,
            retrieved_evidence=[
                evidence.model_copy(deep=True),
            ],
            tool_calls=[
                VendorResearchToolCallTrace(
                    tool_name="search_evidence",
                    query="Find approved vendor profile evidence.",
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


class FakeRiskReportAgent:
    """Deterministic Risk and Report Agent for workflow tests."""

    def __init__(
        self,
        should_fail: bool = False,
        invalid_source_reference: bool = False,
    ) -> None:
        self.should_fail = should_fail
        self.invalid_source_reference = invalid_source_reference
        self.received_inputs: list[RiskReportInput] = []

    async def generate_report(
        self,
        risk_input: RiskReportInput,
    ) -> RiskReportExecution:
        self.received_inputs.append(risk_input)
        if self.should_fail:
            raise RuntimeError("Synthetic Risk and Report Agent failure.")

        proposal_finding = risk_input.proposal_analysis.findings[0]
        source_finding_id = (
            "unknown-finding" if self.invalid_source_reference else proposal_finding.finding_id
        )

        risk = SynthesizedRisk(
            risk_id="risk-001",
            category=RiskCategory.DELIVERY,
            title="Delivery timeline requires validation",
            description="The implementation timeline requires human validation.",
            severity=RiskSeverity.MEDIUM,
            confidence=RiskConfidence.HIGH,
            evidence=[
                RiskEvidenceReference(
                    source_agent="proposal-analysis",
                    source_finding_id=source_finding_id,
                    proposal_evidence=(proposal_finding.evidence[0].model_copy(deep=True)),
                )
            ],
            business_impact="Schedule misalignment may delay go-live.",
            mitigation="Validate milestones and dependencies.",
        )

        result = RiskReportResult(
            assessment_id=risk_input.assessment_id,
            proposal_document_id=risk_input.proposal_document_id,
            vendor_name=risk_input.vendor_name,
            risks=[risk],
            reviewer_report=ReviewerReport(
                title="Proposal and Vendor Risk Review",
                purpose="Support authorized specialist review.",
                sections=[
                    ReportSection(
                        section_id="delivery-risk-section",
                        title="Delivery Risk",
                        content="The delivery timeline requires review.",
                        related_risk_ids=["risk-001"],
                        related_finding_ids=[proposal_finding.finding_id],
                    )
                ],
                required_human_actions=["Validate the delivery schedule."],
            ),
            executive_report=ExecutiveReport(
                title="Executive Proposal Risk Summary",
                executive_summary="A delivery risk requires human review.",
                key_strengths=["The proposal includes a timeline."],
                key_risks=["Schedule alignment is not confirmed."],
                unresolved_decisions=["Confirm the required go-live date."],
                proposed_conditions=["Validate the schedule before approval."],
                decision_disclaimer=RISK_REPORT_DECISION_DISCLAIMER,
            ),
            overall_confidence=RiskConfidence.HIGH,
            human_review_required=True,
            official_decision_provided=False,
        )

        return RiskReportExecution(
            result=result,
            source_proposal_finding_ids=[proposal_finding.finding_id],
            source_vendor_finding_ids=(
                [finding.finding_id for finding in risk_input.vendor_research.findings]
                if risk_input.vendor_research is not None
                else []
            ),
            llm_provider="fake",
            llm_model="fake-model",
            instruction_version="1.0.0",
            total_execution_time_ms=10.0,
        )
