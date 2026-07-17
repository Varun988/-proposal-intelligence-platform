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
from app.evaluation.proposal_analysis import (
    create_proposal_analysis_evaluation_runner,
)


def create_valid_execution() -> ProposalAnalysisExecution:
    """Create an execution that passes both release gates."""

    evidence = EvidenceReference(
        chunk_id="chunk-001",
        document_id="proposal-001",
        file_name="synthetic-proposal.pdf",
        page_number=4,
        citation_label="synthetic-proposal.pdf, page 4",
        supporting_text=("The timeline is twelve months."),
        retrieval_score=0.90,
        final_score=0.95,
    )

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
                recommendation=("Confirm alignment with the target go-live."),
                human_review_required=True,
            )
        ],
        executive_summary=("The proposal states a twelve-month timeline."),
        overall_confidence=FindingConfidence.HIGH,
        human_review_required=True,
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


def test_proposal_evaluation_runner_approves_valid_execution() -> None:
    runner = create_proposal_analysis_evaluation_runner()

    report = runner.run(
        target=create_valid_execution(),
        assessment_id="assessment-001",
        agent_instruction_version="1.0.0",
    )

    assert report.release_approved is True
    assert report.overall_score == 1.0
    assert report.evaluator_count == 2
    assert report.blocking_gate_failure_count == 0


def test_proposal_evaluation_runner_rejects_bad_citation() -> None:
    execution = create_valid_execution()

    execution.result.findings[0].evidence[0].page_number = 99

    runner = create_proposal_analysis_evaluation_runner()

    report = runner.run(
        target=execution,
        assessment_id="assessment-001",
        agent_instruction_version="1.0.0",
    )

    assert report.release_approved is False
    assert report.blocking_gate_failure_count == 1


def test_proposal_evaluation_runner_rejects_bad_trajectory() -> None:
    execution = create_valid_execution()
    execution.result.human_review_required = False

    runner = create_proposal_analysis_evaluation_runner()

    report = runner.run(
        target=execution,
        assessment_id="assessment-001",
        agent_instruction_version="1.0.0",
    )

    assert report.release_approved is False
    assert report.blocking_gate_failure_count == 1
