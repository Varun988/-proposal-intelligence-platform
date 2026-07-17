from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

from app.evaluation.schemas import EvaluationResult

EvaluationTarget = TypeVar(
    "EvaluationTarget",
    bound=BaseModel,
)


class BaseEvaluator[EvaluationTarget: BaseModel](
    ABC,
):
    """Contract implemented by deterministic agent evaluators."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique evaluator name."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the evaluator version."""

    @abstractmethod
    def evaluate(
        self,
        target: EvaluationTarget,
    ) -> EvaluationResult:
        """Evaluate one typed agent execution."""
