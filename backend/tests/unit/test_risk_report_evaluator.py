from copy import deepcopy

from app.evaluation.evaluators.risk_report import (
    RiskReportEvaluator,
)
from app.evaluation.schemas import EvaluationStatus
from tests.risk_report_evaluation_fakes import (
    create_risk_report_execution,
)


def test_evaluator_passes_valid_risk_report() -> None:
    evaluator = RiskReportEvaluator()

    result = evaluator.evaluate(
        create_risk_report_execution(),
    )

    assert result.status is EvaluationStatus.PASSED
    assert result.score == 1.0
    assert result.finding_count == 0
    assert result.metrics["risk_count"] == 1
    assert result.metrics["human_review_required"] is True


def test_evaluator_fails_instruction_version_mismatch() -> None:
    execution = create_risk_report_execution()
    execution.instruction_version = "0.9.0"

    result = RiskReportEvaluator().evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    finding_ids = {finding.finding_id for finding in result.findings}

    assert "risk-report-instruction-version-mismatch" in finding_ids


def test_evaluator_fails_disabled_risk_review() -> None:
    execution = create_risk_report_execution()

    modified_risk = deepcopy(execution.result.risks[0])
    modified_risk.human_review_required = False

    execution.result.risks = [modified_risk]

    result = RiskReportEvaluator().evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    assert any(
        finding.finding_id.startswith("risk-human-review-disabled") for finding in result.findings
    )


def test_evaluator_fails_unknown_source_finding() -> None:
    execution = create_risk_report_execution()

    execution.result.risks[0].evidence[0].source_finding_id = "unknown-finding"

    result = RiskReportEvaluator().evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    assert any(
        finding.finding_id.startswith("unknown-proposal-risk-source") for finding in result.findings
    )


def test_evaluator_fails_unknown_report_risk_reference() -> None:
    execution = create_risk_report_execution()

    execution.result.reviewer_report.sections[0].related_risk_ids = [
        "unknown-risk",
    ]

    result = RiskReportEvaluator().evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    assert any(
        finding.finding_id.startswith("unknown-report-risk-reference")
        for finding in result.findings
    )


def test_evaluator_fails_unknown_report_finding_reference() -> None:
    execution = create_risk_report_execution()

    execution.result.reviewer_report.sections[0].related_finding_ids = [
        "unknown-finding",
    ]

    result = RiskReportEvaluator().evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    assert any(
        finding.finding_id.startswith("unknown-report-finding-reference")
        for finding in result.findings
    )


def test_evaluator_warns_for_duplicate_section_id() -> None:
    execution = create_risk_report_execution()

    section = execution.result.reviewer_report.sections[0]

    execution.result.reviewer_report.sections = [
        section,
        deepcopy(section),
    ]

    result = RiskReportEvaluator().evaluate(execution)

    assert result.status is EvaluationStatus.WARNING
    assert result.score < 1.0

    assert any(
        finding.finding_id.startswith("duplicate-report-section") for finding in result.findings
    )
