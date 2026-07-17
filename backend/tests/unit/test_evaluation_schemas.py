import pytest
from pydantic import ValidationError

from app.evaluation.schemas import (
    AgentEvaluationReport,
    EvaluationFinding,
    EvaluationGateResult,
    EvaluationResult,
    EvaluationSeverity,
    EvaluationStatus,
)


def test_evaluation_result_reports_success() -> None:
    result = EvaluationResult(
        evaluator_name="citation-evaluator",
        evaluator_version="1.0.0",
        status=EvaluationStatus.PASSED,
        score=1.0,
        summary="All findings contain valid citations.",
    )

    assert result.passed is True
    assert result.finding_count == 0
    assert result.critical_finding_count == 0


def test_evaluation_result_counts_findings() -> None:
    result = EvaluationResult(
        evaluator_name="citation-evaluator",
        evaluator_version="1.0.0",
        status=EvaluationStatus.FAILED,
        score=0.5,
        summary="One finding has no citation.",
        findings=[
            EvaluationFinding(
                finding_id="missing-citation-001",
                description=("The finding does not include evidence."),
                severity=EvaluationSeverity.CRITICAL,
                location="result.findings[0]",
            ),
            EvaluationFinding(
                finding_id="warning-001",
                description=("A citation score is unavailable."),
                severity=EvaluationSeverity.LOW,
            ),
        ],
    )

    assert result.passed is False
    assert result.finding_count == 2
    assert result.critical_finding_count == 1


def test_evaluation_result_preserves_metrics() -> None:
    result = EvaluationResult(
        evaluator_name="trajectory-evaluator",
        evaluator_version="1.0.0",
        status=EvaluationStatus.PASSED,
        score=1.0,
        summary="The agent trajectory is valid.",
        metrics={
            "tool_call_count": 3,
            "maximum_tool_calls": 15,
            "used_only_allowed_tools": True,
        },
    )

    assert result.metrics["tool_call_count"] == 3
    assert result.metrics["maximum_tool_calls"] == 15
    assert result.metrics["used_only_allowed_tools"] is True


def test_evaluation_result_rejects_score_above_one() -> None:
    with pytest.raises(ValidationError):
        EvaluationResult(
            evaluator_name="invalid-evaluator",
            evaluator_version="1.0.0",
            status=EvaluationStatus.FAILED,
            score=1.5,
            summary="Invalid score.",
        )


def test_evaluation_result_rejects_negative_score() -> None:
    with pytest.raises(ValidationError):
        EvaluationResult(
            evaluator_name="invalid-evaluator",
            evaluator_version="1.0.0",
            status=EvaluationStatus.FAILED,
            score=-0.1,
            summary="Invalid score.",
        )


def test_agent_evaluation_report_counts_failures() -> None:
    passing_result = EvaluationResult(
        evaluator_name="identity-evaluator",
        evaluator_version="1.0.0",
        status=EvaluationStatus.PASSED,
        score=1.0,
        summary="Identity validation passed.",
    )

    failing_result = EvaluationResult(
        evaluator_name="citation-evaluator",
        evaluator_version="1.0.0",
        status=EvaluationStatus.FAILED,
        score=0.4,
        summary="Citation validation failed.",
    )

    report = AgentEvaluationReport(
        evaluation_id="evaluation-001",
        agent_name="proposal-analysis",
        assessment_id="assessment-001",
        agent_instruction_version="1.0.0",
        results=[
            passing_result,
            failing_result,
        ],
        gate_results=[
            EvaluationGateResult(
                evaluator_name="citation-evaluator",
                passed=False,
                blocking=True,
                actual_score=0.4,
                minimum_score=0.95,
                actual_status=EvaluationStatus.FAILED,
                required_status=EvaluationStatus.PASSED,
                message="Citation gate failed.",
            )
        ],
        release_approved=False,
        overall_score=0.7,
    )

    assert report.evaluator_count == 2
    assert report.failed_evaluator_count == 1
    assert report.blocking_gate_failure_count == 1
    assert report.release_approved is False


def test_agent_evaluation_report_counts_no_failures() -> None:
    passing_result = EvaluationResult(
        evaluator_name="identity-evaluator",
        evaluator_version="1.0.0",
        status=EvaluationStatus.PASSED,
        score=1.0,
        summary="Identity validation passed.",
    )

    report = AgentEvaluationReport(
        evaluation_id="evaluation-001",
        agent_name="proposal-analysis",
        assessment_id="assessment-001",
        agent_instruction_version="1.0.0",
        results=[
            passing_result,
        ],
        gate_results=[
            EvaluationGateResult(
                evaluator_name="identity-evaluator",
                passed=True,
                blocking=True,
                actual_score=1.0,
                minimum_score=1.0,
                actual_status=EvaluationStatus.PASSED,
                required_status=EvaluationStatus.PASSED,
                message="Identity gate passed.",
            )
        ],
        release_approved=True,
        overall_score=1.0,
    )

    assert report.evaluator_count == 1
    assert report.failed_evaluator_count == 0
    assert report.blocking_gate_failure_count == 0
    assert report.release_approved is True


def test_evaluation_finding_preserves_traceability() -> None:
    finding = EvaluationFinding(
        finding_id="missing-citation-001",
        description=("A high-confidence finding has no supporting evidence."),
        severity=EvaluationSeverity.CRITICAL,
        location="result.findings[0]",
        related_ids=[
            "finding-001",
            "assessment-001",
        ],
        metadata={
            "confidence": "high",
            "finding_category": "delivery",
        },
    )

    assert finding.finding_id == "missing-citation-001"
    assert finding.location == "result.findings[0]"
    assert finding.related_ids == [
        "finding-001",
        "assessment-001",
    ]
    assert finding.metadata["confidence"] == "high"
    assert finding.metadata["finding_category"] == "delivery"
