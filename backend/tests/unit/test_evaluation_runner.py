import pytest

from app.agents.proposal_analysis.schemas import (
    AgentToolCallTrace,
    FindingConfidence,
    ProposalAnalysisExecution,
    ProposalAnalysisResult,
    ProposalSummary,
)
from app.core.exceptions import (
    EvaluationConfigurationError,
    EvaluationExecutionError,
)
from app.evaluation.runner import AgentEvaluationRunner
from app.evaluation.schemas import (
    EvaluationGate,
    EvaluationStatus,
)
from tests.evaluation_fakes import (
    FakeFailingEvaluator,
    FakePassingEvaluator,
)


def create_execution() -> ProposalAnalysisExecution:
    """Create a minimal synthetic agent execution."""

    result = ProposalAnalysisResult(
        assessment_id="assessment-001",
        proposal_document_id="proposal-001",
        summary=ProposalSummary(
            delivery_timeline="Twelve months",
        ),
        executive_summary=("The proposal includes a twelve-month delivery timeline."),
        overall_confidence=FindingConfidence.LOW,
        human_review_required=True,
    )

    return ProposalAnalysisExecution(
        result=result,
        retrieved_evidence=[],
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


def test_runner_approves_passing_blocking_gate() -> None:
    runner = AgentEvaluationRunner(
        agent_name="proposal-analysis",
        evaluators=[
            FakePassingEvaluator(),
        ],
        gates=[
            EvaluationGate(
                evaluator_name=("fake-passing-evaluator"),
                minimum_score=0.95,
                required_status=EvaluationStatus.PASSED,
                blocking=True,
            )
        ],
    )

    report = runner.run(
        target=create_execution(),
        assessment_id="assessment-001",
        agent_instruction_version="1.0.0",
    )

    assert report.release_approved is True
    assert report.overall_score == 1.0
    assert report.evaluator_count == 1
    assert report.failed_evaluator_count == 0
    assert report.blocking_gate_failure_count == 0
    assert len(report.evaluation_id) > 0


def test_runner_rejects_failed_blocking_gate() -> None:
    runner = AgentEvaluationRunner(
        agent_name="proposal-analysis",
        evaluators=[
            FakeFailingEvaluator(),
        ],
        gates=[
            EvaluationGate(
                evaluator_name=("fake-failing-evaluator"),
                minimum_score=0.90,
                required_status=EvaluationStatus.PASSED,
                blocking=True,
            )
        ],
    )

    report = runner.run(
        target=create_execution(),
        assessment_id="assessment-001",
        agent_instruction_version="1.0.0",
    )

    assert report.release_approved is False
    assert report.overall_score == 0.25
    assert report.failed_evaluator_count == 1
    assert report.blocking_gate_failure_count == 1


def test_runner_allows_failed_non_blocking_gate() -> None:
    runner = AgentEvaluationRunner(
        agent_name="proposal-analysis",
        evaluators=[
            FakeFailingEvaluator(),
        ],
        gates=[
            EvaluationGate(
                evaluator_name=("fake-failing-evaluator"),
                minimum_score=0.90,
                required_status=EvaluationStatus.PASSED,
                blocking=False,
            )
        ],
    )

    report = runner.run(
        target=create_execution(),
        assessment_id="assessment-001",
        agent_instruction_version="1.0.0",
    )

    assert report.release_approved is True
    assert report.gate_results[0].passed is False
    assert report.gate_results[0].blocking is False


def test_runner_calculates_average_score() -> None:
    runner = AgentEvaluationRunner(
        agent_name="proposal-analysis",
        evaluators=[
            FakePassingEvaluator(),
            FakeFailingEvaluator(),
        ],
        gates=[],
    )

    report = runner.run(
        target=create_execution(),
        assessment_id="assessment-001",
        agent_instruction_version="1.0.0",
    )

    assert report.overall_score == pytest.approx(
        0.625,
    )
    assert report.evaluator_count == 2


def test_runner_preserves_metadata() -> None:
    runner = AgentEvaluationRunner(
        agent_name="proposal-analysis",
        evaluators=[
            FakePassingEvaluator(),
        ],
        gates=[],
    )

    report = runner.run(
        target=create_execution(),
        assessment_id="assessment-001",
        agent_instruction_version="1.0.0",
    )

    assert report.agent_name == "proposal-analysis"
    assert report.assessment_id == "assessment-001"
    assert report.agent_instruction_version == "1.0.0"


def test_runner_rejects_duplicate_evaluator_names() -> None:
    with pytest.raises(
        EvaluationConfigurationError,
        match="Duplicate evaluator names",
    ):
        AgentEvaluationRunner(
            agent_name="proposal-analysis",
            evaluators=[
                FakePassingEvaluator(),
                FakePassingEvaluator(),
            ],
            gates=[],
        )


def test_runner_rejects_gate_for_unknown_evaluator() -> None:
    with pytest.raises(
        EvaluationConfigurationError,
        match="unregistered evaluator",
    ):
        AgentEvaluationRunner(
            agent_name="proposal-analysis",
            evaluators=[
                FakePassingEvaluator(),
            ],
            gates=[
                EvaluationGate(
                    evaluator_name="unknown-evaluator",
                    minimum_score=0.90,
                )
            ],
        )


def test_runner_rejects_empty_evaluator_collection() -> None:
    with pytest.raises(
        EvaluationConfigurationError,
        match="At least one evaluator",
    ):
        AgentEvaluationRunner(
            agent_name="proposal-analysis",
            evaluators=[],
            gates=[],
        )


def test_runner_rejects_empty_agent_name() -> None:
    with pytest.raises(
        EvaluationConfigurationError,
        match="agent name cannot be empty",
    ):
        AgentEvaluationRunner(
            agent_name=" ",
            evaluators=[
                FakePassingEvaluator(),
            ],
            gates=[],
        )


@pytest.mark.parametrize(
    (
        "assessment_id",
        "instruction_version",
        "expected_message",
    ),
    [
        (
            "",
            "1.0.0",
            "assessment ID cannot be empty",
        ),
        (
            "assessment-001",
            "",
            "instruction version cannot be empty",
        ),
    ],
)
def test_runner_rejects_empty_execution_metadata(
    assessment_id: str,
    instruction_version: str,
    expected_message: str,
) -> None:
    runner = AgentEvaluationRunner(
        agent_name="proposal-analysis",
        evaluators=[
            FakePassingEvaluator(),
        ],
        gates=[],
    )

    with pytest.raises(
        EvaluationConfigurationError,
        match=expected_message,
    ):
        runner.run(
            target=create_execution(),
            assessment_id=assessment_id,
            agent_instruction_version=(instruction_version),
        )


class InvalidNameEvaluator(FakePassingEvaluator):
    """Evaluator returning a mismatched result name."""

    def evaluate(
        self,
        target: ProposalAnalysisExecution,
    ):
        result = super().evaluate(target)

        return result.model_copy(
            update={
                "evaluator_name": "unexpected-name",
            }
        )


def test_runner_rejects_mismatched_result_name() -> None:
    runner = AgentEvaluationRunner(
        agent_name="proposal-analysis",
        evaluators=[
            InvalidNameEvaluator(),
        ],
        gates=[],
    )

    with pytest.raises(
        EvaluationExecutionError,
        match="result name does not match",
    ):
        runner.run(
            target=create_execution(),
            assessment_id="assessment-001",
            agent_instruction_version="1.0.0",
        )
