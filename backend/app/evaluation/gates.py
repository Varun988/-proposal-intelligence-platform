from app.evaluation.schemas import (
    EvaluationGate,
    EvaluationGateResult,
    EvaluationResult,
)


def evaluate_gate(
    result: EvaluationResult,
    gate: EvaluationGate,
) -> EvaluationGateResult:
    """Apply one release gate to an evaluation result."""

    if result.evaluator_name != gate.evaluator_name:
        raise ValueError("Evaluation result and gate evaluator names must match.")

    status_passed = result.status is gate.required_status
    score_passed = result.score >= gate.minimum_score
    gate_passed = status_passed and score_passed

    if gate_passed:
        message = f"Evaluator '{result.evaluator_name}' passed its release gate."
    else:
        message = f"Evaluator '{result.evaluator_name}' failed its release gate."

    return EvaluationGateResult(
        evaluator_name=result.evaluator_name,
        passed=gate_passed,
        blocking=gate.blocking,
        actual_score=result.score,
        minimum_score=gate.minimum_score,
        actual_status=result.status,
        required_status=gate.required_status,
        message=message,
    )
