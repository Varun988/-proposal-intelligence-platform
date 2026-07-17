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
