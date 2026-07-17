import pytest

from app.evaluation.gates import evaluate_gate
from app.evaluation.schemas import (
    EvaluationGate,
    EvaluationResult,
    EvaluationStatus,
)


def test_release_gate_passes_valid_result() -> None:
    result = EvaluationResult(
        evaluator_name="citation-evaluator",
        evaluator_version="1.0.0",
        status=EvaluationStatus.PASSED,
        score=0.98,
        summary="Citation evaluation passed.",
    )

    gate = EvaluationGate(
        evaluator_name="citation-evaluator",
        minimum_score=0.95,
        required_status=EvaluationStatus.PASSED,
        blocking=True,
    )

    gate_result = evaluate_gate(
        result=result,
        gate=gate,
    )

    assert gate_result.passed is True
    assert gate_result.blocking is True
    assert gate_result.actual_score == 0.98


def test_release_gate_fails_low_score() -> None:
    result = EvaluationResult(
        evaluator_name="citation-evaluator",
        evaluator_version="1.0.0",
        status=EvaluationStatus.PASSED,
        score=0.80,
        summary="Citation score is below threshold.",
    )

    gate = EvaluationGate(
        evaluator_name="citation-evaluator",
        minimum_score=0.95,
        blocking=True,
    )

    gate_result = evaluate_gate(
        result=result,
        gate=gate,
    )

    assert gate_result.passed is False
    assert "failed" in gate_result.message.casefold()


def test_release_gate_fails_wrong_status() -> None:
    result = EvaluationResult(
        evaluator_name="trajectory-evaluator",
        evaluator_version="1.0.0",
        status=EvaluationStatus.WARNING,
        score=1.0,
        summary="Trajectory generated a warning.",
    )

    gate = EvaluationGate(
        evaluator_name="trajectory-evaluator",
        minimum_score=0.90,
        required_status=EvaluationStatus.PASSED,
    )

    gate_result = evaluate_gate(
        result=result,
        gate=gate,
    )

    assert gate_result.passed is False


def test_release_gate_rejects_mismatched_evaluator() -> None:
    result = EvaluationResult(
        evaluator_name="citation-evaluator",
        evaluator_version="1.0.0",
        status=EvaluationStatus.PASSED,
        score=1.0,
        summary="Citation evaluation passed.",
    )

    gate = EvaluationGate(
        evaluator_name="trajectory-evaluator",
        minimum_score=0.90,
    )

    with pytest.raises(
        ValueError,
        match="evaluator names must match",
    ):
        evaluate_gate(
            result=result,
            gate=gate,
        )
