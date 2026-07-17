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
