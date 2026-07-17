from collections.abc import Sequence
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from app.core.exceptions import (
    EvaluationConfigurationError,
    EvaluationExecutionError,
)
from app.evaluation.evaluators.base import BaseEvaluator
from app.evaluation.gates import evaluate_gate
from app.evaluation.schemas import (
    AgentEvaluationReport,
    EvaluationGate,
    EvaluationGateResult,
    EvaluationResult,
)


class AgentEvaluationRunner:
    """Run agent evaluators and apply configured release gates."""

    def __init__(
        self,
        agent_name: str,
        evaluators: Sequence[BaseEvaluator[Any]],
        gates: Sequence[EvaluationGate],
    ) -> None:
        normalized_agent_name = agent_name.strip()

        if not normalized_agent_name:
            raise EvaluationConfigurationError("Evaluation agent name cannot be empty.")

        if not evaluators:
            raise EvaluationConfigurationError("At least one evaluator must be configured.")

        self._agent_name = normalized_agent_name
        self._evaluators = tuple(evaluators)
        self._gates = tuple(gates)

        self._validate_configuration()

    @property
    def agent_name(self) -> str:
        """Return the agent evaluated by this runner."""

        return self._agent_name

    @property
    def evaluator_names(self) -> tuple[str, ...]:
        """Return configured evaluator names in execution order."""

        return tuple(evaluator.name for evaluator in self._evaluators)

    @property
    def gate_count(self) -> int:
        """Return the number of configured release gates."""

        return len(self._gates)

    def run(
        self,
        target: BaseModel,
        assessment_id: str,
        agent_instruction_version: str,
    ) -> AgentEvaluationReport:
        """Execute evaluators and produce a release-gate report."""

        normalized_assessment_id = assessment_id.strip()
        normalized_instruction_version = agent_instruction_version.strip()

        if not normalized_assessment_id:
            raise EvaluationConfigurationError("Evaluation assessment ID cannot be empty.")

        if not normalized_instruction_version:
            raise EvaluationConfigurationError("Agent instruction version cannot be empty.")

        evaluation_results = [
            self._run_evaluator(
                evaluator=evaluator,
                target=target,
            )
            for evaluator in self._evaluators
        ]

        results_by_name = {result.evaluator_name: result for result in evaluation_results}

        gate_results = [
            self._apply_gate(
                gate=gate,
                results_by_name=results_by_name,
            )
            for gate in self._gates
        ]

        overall_score = self._calculate_overall_score(
            evaluation_results,
        )

        release_approved = not any(
            gate_result.blocking and not gate_result.passed for gate_result in gate_results
        )

        return AgentEvaluationReport(
            evaluation_id=str(uuid4()),
            agent_name=self.agent_name,
            assessment_id=normalized_assessment_id,
            agent_instruction_version=(normalized_instruction_version),
            results=evaluation_results,
            gate_results=gate_results,
            release_approved=release_approved,
            overall_score=overall_score,
        )

    def _validate_configuration(self) -> None:
        """Validate evaluator names and release-gate references."""

        evaluator_names = [evaluator.name.strip() for evaluator in self._evaluators]

        if any(not evaluator_name for evaluator_name in evaluator_names):
            raise EvaluationConfigurationError("Evaluator names cannot be empty.")

        duplicate_names = {
            evaluator_name
            for evaluator_name in evaluator_names
            if evaluator_names.count(evaluator_name) > 1
        }

        if duplicate_names:
            duplicate_text = ", ".join(sorted(duplicate_names))

            raise EvaluationConfigurationError(
                f"Duplicate evaluator names are not allowed: {duplicate_text}."
            )

        registered_names = set(evaluator_names)

        for gate in self._gates:
            if gate.evaluator_name not in registered_names:
                raise EvaluationConfigurationError(
                    f"Release gate references an unregistered evaluator: {gate.evaluator_name}."
                )

    @staticmethod
    def _run_evaluator(
        evaluator: BaseEvaluator[Any],
        target: BaseModel,
    ) -> EvaluationResult:
        """Execute one evaluator with normalized error handling."""

        try:
            result = evaluator.evaluate(target)
        except Exception as error:
            raise EvaluationExecutionError(
                f"Evaluator '{evaluator.name}' execution failed."
            ) from error

        if result.evaluator_name != evaluator.name:
            raise EvaluationExecutionError(
                f"Evaluator result name does not match the configured evaluator: {evaluator.name}."
            )

        if result.evaluator_version != evaluator.version:
            raise EvaluationExecutionError(
                "Evaluator result version does not match the "
                f"configured evaluator version: {evaluator.name}."
            )

        return result

    @staticmethod
    def _apply_gate(
        gate: EvaluationGate,
        results_by_name: dict[str, EvaluationResult],
    ) -> EvaluationGateResult:
        """Apply one gate to its corresponding evaluator result."""

        result = results_by_name.get(
            gate.evaluator_name,
        )

        if result is None:
            raise EvaluationExecutionError(
                f"No evaluation result exists for release gate '{gate.evaluator_name}'."
            )

        return evaluate_gate(
            result=result,
            gate=gate,
        )

    @staticmethod
    def _calculate_overall_score(
        results: list[EvaluationResult],
    ) -> float:
        """Calculate the arithmetic mean evaluator score."""

        if not results:
            return 0.0

        return sum(result.score for result in results) / len(results)
