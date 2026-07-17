from app.evaluation.risk_report import (
    create_risk_report_evaluation_runner,
)
from tests.risk_report_evaluation_fakes import (
    create_risk_report_execution,
)


def test_runner_approves_valid_risk_report() -> None:
    runner = create_risk_report_evaluation_runner()

    report = runner.run(
        target=create_risk_report_execution(),
        assessment_id="assessment-001",
        agent_instruction_version="1.0.0",
    )

    assert report.release_approved is True
    assert report.overall_score == 1.0
    assert report.evaluator_count == 1
    assert report.blocking_gate_failure_count == 0


def test_runner_rejects_invalid_source_reference() -> None:
    execution = create_risk_report_execution()

    execution.result.risks[
        0
    ].evidence[0].source_finding_id = (
        "unknown-finding"
    )

    runner = create_risk_report_evaluation_runner()

    report = runner.run(
        target=execution,
        assessment_id="assessment-001",
        agent_instruction_version="1.0.0",
    )

    assert report.release_approved is False
    assert report.blocking_gate_failure_count == 1


def test_runner_rejects_invalid_report_reference() -> None:
    execution = create_risk_report_execution()

    execution.result.reviewer_report.sections[
        0
    ].related_risk_ids = [
        "unknown-risk",
    ]

    runner = create_risk_report_evaluation_runner()

    report = runner.run(
        target=execution,
        assessment_id="assessment-001",
        agent_instruction_version="1.0.0",
    )

    assert report.release_approved is False
    assert report.blocking_gate_failure_count == 1