from app.evaluation.vendor_research import (
    create_vendor_research_evaluation_runner,
)
from tests.unit.test_vendor_research_trajectory_evaluator import (
    create_execution,
)


def test_runner_approves_valid_vendor_research() -> None:
    runner = create_vendor_research_evaluation_runner()

    report = runner.run(
        target=create_execution(),
        assessment_id="assessment-001",
        agent_instruction_version="1.0.0",
    )

    assert report.release_approved is True
    assert report.overall_score == 1.0
    assert report.evaluator_count == 2
    assert report.blocking_gate_failure_count == 0


def test_runner_rejects_invalid_vendor_citation() -> None:
    execution = create_execution()

    execution.result.findings[0].evidence[0].page_number = 99

    runner = create_vendor_research_evaluation_runner()

    report = runner.run(
        target=execution,
        assessment_id="assessment-001",
        agent_instruction_version="1.0.0",
    )

    assert report.release_approved is False
    assert report.blocking_gate_failure_count == 1


def test_runner_rejects_invalid_vendor_trajectory() -> None:
    execution = create_execution()
    execution.result.human_review_required = False

    runner = create_vendor_research_evaluation_runner()

    report = runner.run(
        target=execution,
        assessment_id="assessment-001",
        agent_instruction_version="1.0.0",
    )

    assert report.release_approved is False
    assert report.blocking_gate_failure_count == 1
