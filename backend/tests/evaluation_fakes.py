from app.agents.proposal_analysis.schemas import (
    ProposalAnalysisExecution,
)
from app.evaluation.evaluators.base import BaseEvaluator
from app.evaluation.schemas import (
    EvaluationFinding,
    EvaluationResult,
    EvaluationSeverity,
    EvaluationStatus,
)


class FakePassingEvaluator(
    BaseEvaluator[ProposalAnalysisExecution],
):
    """Deterministic passing evaluator used by unit tests."""

    @property
    def name(self) -> str:
        return "fake-passing-evaluator"

    @property
    def version(self) -> str:
        return "1.0.0"

    def evaluate(
        self,
        target: ProposalAnalysisExecution,
    ) -> EvaluationResult:
        return EvaluationResult(
            evaluator_name=self.name,
            evaluator_version=self.version,
            status=EvaluationStatus.PASSED,
            score=1.0,
            summary=("The synthetic agent execution passed evaluation."),
            findings=[],
            metrics={
                "tool_call_count": target.tool_call_count,
            },
        )


class FakeFailingEvaluator(
    BaseEvaluator[ProposalAnalysisExecution],
):
    """Deterministic failing evaluator used by unit tests."""

    @property
    def name(self) -> str:
        return "fake-failing-evaluator"

    @property
    def version(self) -> str:
        return "1.0.0"

    def evaluate(
        self,
        target: ProposalAnalysisExecution,
    ) -> EvaluationResult:
        return EvaluationResult(
            evaluator_name=self.name,
            evaluator_version=self.version,
            status=EvaluationStatus.FAILED,
            score=0.25,
            summary=("The synthetic agent execution failed evaluation."),
            findings=[
                EvaluationFinding(
                    finding_id="evaluation-finding-001",
                    description=("Synthetic critical evaluation failure."),
                    severity=EvaluationSeverity.CRITICAL,
                    location="result.findings[0]",
                    related_ids=[
                        target.result.assessment_id,
                    ],
                )
            ],
            metrics={
                "tool_call_count": target.tool_call_count,
            },
        )
