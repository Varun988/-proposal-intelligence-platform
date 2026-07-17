from copy import deepcopy

from app.agents.proposal_analysis.schemas import (
    AgentToolCallTrace,
    FindingCategory,
    FindingConfidence,
    FindingSeverity,
    ProposalAnalysisExecution,
    ProposalAnalysisResult,
    ProposalFinding,
    ProposalSummary,
)
from app.evaluation.evaluators.trajectory import (
    ProposalTrajectoryEvaluator,
)
from app.evaluation.schemas import EvaluationStatus


def create_execution() -> ProposalAnalysisExecution:
    """Create a valid synthetic proposal-analysis execution."""

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
                title="Delivery timeline identified",
                description=("The proposal states a twelve-month delivery timeline."),
                severity=FindingSeverity.MEDIUM,
                confidence=FindingConfidence.LOW,
                recommendation=("Confirm the timeline during human review."),
                human_review_required=True,
            )
        ],
        executive_summary=("The proposal includes a twelve-month timeline."),
        overall_confidence=FindingConfidence.LOW,
        human_review_required=True,
    )

    return ProposalAnalysisExecution(
        result=result,
        retrieved_evidence=[],
        tool_calls=[
            AgentToolCallTrace(
                tool_name="search_evidence",
                query=("Find proposal evidence about delivery timeline."),
                succeeded=True,
                execution_time_ms=1.5,
                result_count=1,
            )
        ],
        tool_call_count=1,
        llm_provider="fake",
        llm_model="fake-model",
        instruction_version="1.0.0",
        total_execution_time_ms=10.0,
    )


def test_evaluator_passes_valid_trajectory() -> None:
    evaluator = ProposalTrajectoryEvaluator()

    result = evaluator.evaluate(
        create_execution(),
    )

    assert result.status is EvaluationStatus.PASSED
    assert result.score == 1.0
    assert result.finding_count == 0
    assert result.metrics["required_tool_used"] is True
    assert result.metrics["successful_tool_calls"] == 1


def test_evaluator_fails_tool_count_mismatch() -> None:
    execution = create_execution()
    execution.tool_call_count = 2

    evaluator = ProposalTrajectoryEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED
    assert result.score < 1.0

    finding_ids = {finding.finding_id for finding in result.findings}

    assert "tool-call-count-mismatch" in finding_ids


def test_evaluator_fails_tool_call_limit() -> None:
    execution = create_execution()
    execution.tool_call_count = 2

    execution.tool_calls.append(
        AgentToolCallTrace(
            tool_name="search_evidence",
            query="Find pricing evidence.",
            succeeded=True,
            execution_time_ms=1.0,
            result_count=1,
        )
    )

    evaluator = ProposalTrajectoryEvaluator(
        maximum_tool_calls=1,
    )
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    finding_ids = {finding.finding_id for finding in result.findings}

    assert "tool-call-limit-exceeded" in finding_ids


def test_evaluator_fails_unauthorized_tool() -> None:
    execution = create_execution()

    execution.tool_calls.append(
        AgentToolCallTrace(
            tool_name="delete_document",
            query=None,
            succeeded=True,
            execution_time_ms=1.0,
            result_count=0,
        )
    )
    execution.tool_call_count = 2

    evaluator = ProposalTrajectoryEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    assert any(finding.finding_id.startswith("unauthorized-tool") for finding in result.findings)


def test_evaluator_fails_missing_required_tool() -> None:
    execution = create_execution()
    execution.tool_calls = [
        AgentToolCallTrace(
            tool_name="get_document_page",
            query=None,
            succeeded=True,
            execution_time_ms=1.0,
            result_count=1,
        )
    ]

    evaluator = ProposalTrajectoryEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    finding_ids = {finding.finding_id for finding in result.findings}

    assert "required-tool-not-used" in finding_ids


def test_evaluator_fails_unsuccessful_tool_call() -> None:
    execution = create_execution()

    execution.tool_calls[0] = AgentToolCallTrace(
        tool_name="search_evidence",
        query="Find delivery timeline evidence.",
        succeeded=False,
        execution_time_ms=1.0,
        result_count=0,
        error_message="Synthetic search failure.",
    )

    evaluator = ProposalTrajectoryEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED
    assert result.metrics["failed_tool_calls"] == 1


def test_evaluator_fails_missing_search_query() -> None:
    execution = create_execution()
    execution.tool_calls[0].query = None

    evaluator = ProposalTrajectoryEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    assert any(finding.finding_id.startswith("missing-search-query") for finding in result.findings)


def test_evaluator_warns_for_empty_search_result() -> None:
    execution = create_execution()
    execution.tool_calls[0].result_count = 0

    evaluator = ProposalTrajectoryEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.WARNING
    assert result.score < 1.0
    assert result.metrics["result_bearing_tool_calls"] == 0


def test_evaluator_fails_instruction_version_mismatch() -> None:
    execution = create_execution()
    execution.instruction_version = "0.9.0"

    evaluator = ProposalTrajectoryEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    finding_ids = {finding.finding_id for finding in result.findings}

    assert "instruction-version-mismatch" in finding_ids


def test_evaluator_fails_disabled_human_review() -> None:
    execution = create_execution()
    execution.result.human_review_required = False

    evaluator = ProposalTrajectoryEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    finding_ids = {finding.finding_id for finding in result.findings}

    assert "human-review-disabled" in finding_ids


def test_evaluator_fails_finding_without_human_review() -> None:
    execution = create_execution()

    modified_finding = deepcopy(execution.result.findings[0])
    modified_finding.human_review_required = False

    execution.result.findings = [
        modified_finding,
    ]

    evaluator = ProposalTrajectoryEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    assert any(
        finding.finding_id.startswith("finding-human-review-disabled")
        for finding in result.findings
    )


def test_evaluator_rejects_invalid_maximum_tool_calls() -> None:
    try:
        ProposalTrajectoryEvaluator(
            maximum_tool_calls=0,
        )
    except ValueError as error:
        assert "must be at least 1" in str(error)
    else:
        raise AssertionError("Expected invalid tool-call limit to fail.")
