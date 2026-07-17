from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, computed_field


class EvaluationStatus(StrEnum):
    """Possible outcomes of an evaluation."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    NOT_APPLICABLE = "not_applicable"


class EvaluationSeverity(StrEnum):
    """Importance of an evaluation result."""

    CRITICAL = "critical"
    HIGH = "high"
    LOW = "low"
    MEDIUM = "medium"


class EvaluationFinding(BaseModel):
    """One detailed issue detected by an evaluator."""

    finding_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    severity: EvaluationSeverity
    location: str | None = None
    related_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    """Result returned by one deterministic evaluator."""

    evaluator_name: str = Field(min_length=1)
    evaluator_version: str = Field(min_length=1)
    status: EvaluationStatus
    score: float = Field(ge=0.0, le=1.0)
    summary: str = Field(min_length=1)

    findings: list[EvaluationFinding] = Field(
        default_factory=list,
    )
    metrics: dict[str, int | float | str | bool | None] = Field(
        default_factory=dict,
    )

    @computed_field
    @property
    def passed(self) -> bool:
        """Return whether the evaluation passed."""

        return self.status is EvaluationStatus.PASSED

    @computed_field
    @property
    def finding_count(self) -> int:
        """Return the number of evaluation findings."""

        return len(self.findings)

    @computed_field
    @property
    def critical_finding_count(self) -> int:
        """Return the number of critical findings."""

        return sum(
            1 for finding in self.findings if finding.severity is EvaluationSeverity.CRITICAL
        )


class EvaluationGate(BaseModel):
    """Release-gate rule applied to evaluation results."""

    evaluator_name: str = Field(min_length=1)
    minimum_score: float = Field(ge=0.0, le=1.0)
    required_status: EvaluationStatus = EvaluationStatus.PASSED
    blocking: bool = True


class EvaluationGateResult(BaseModel):
    """Outcome of applying one release gate."""

    evaluator_name: str = Field(min_length=1)
    passed: bool
    blocking: bool
    actual_score: float = Field(ge=0.0, le=1.0)
    minimum_score: float = Field(ge=0.0, le=1.0)
    actual_status: EvaluationStatus
    required_status: EvaluationStatus
    message: str = Field(min_length=1)


class AgentEvaluationReport(BaseModel):
    """Consolidated evaluation report for one agent execution."""

    evaluation_id: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    assessment_id: str = Field(min_length=1)
    agent_instruction_version: str = Field(min_length=1)

    results: list[EvaluationResult] = Field(
        default_factory=list,
    )
    gate_results: list[EvaluationGateResult] = Field(
        default_factory=list,
    )

    release_approved: bool
    overall_score: float = Field(ge=0.0, le=1.0)

    @computed_field
    @property
    def evaluator_count(self) -> int:
        """Return the number of evaluators executed."""

        return len(self.results)

    @computed_field
    @property
    def failed_evaluator_count(self) -> int:
        """Return the number of failed evaluators."""

        return sum(1 for result in self.results if result.status is EvaluationStatus.FAILED)

    @computed_field
    @property
    def blocking_gate_failure_count(self) -> int:
        """Return the number of failed blocking gates."""

        return sum(
            1
            for gate_result in self.gate_results
            if gate_result.blocking and not gate_result.passed
        )
