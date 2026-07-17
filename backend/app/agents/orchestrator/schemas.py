from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class SpecialistAgentName(StrEnum):
    """Specialist agents available to the orchestrator."""

    PROPOSAL_ANALYSIS = "proposal-analysis"
    RISK_REPORT = "risk-report"
    VENDOR_RESEARCH = "vendor-research"


class OrchestrationPriority(StrEnum):
    """Priority assigned to an orchestration task."""

    HIGH = "high"
    LOW = "low"
    MEDIUM = "medium"


class OrchestrationTaskStatus(StrEnum):
    """Execution status of an orchestration task."""

    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING = "pending"
    RUNNING = "running"
    SKIPPED = "skipped"


class OrchestrationTask(BaseModel):
    """One bounded specialist-agent task in an execution plan."""

    task_id: str = Field(min_length=1)
    agent_name: SpecialistAgentName
    objective: str = Field(min_length=1)
    priority: OrchestrationPriority = OrchestrationPriority.MEDIUM
    status: OrchestrationTaskStatus = OrchestrationTaskStatus.PENDING

    depends_on: list[str] = Field(
        default_factory=list,
    )
    required: bool = True
    maximum_retries: int = Field(default=1, ge=0, le=3)
    metadata: dict[
        str,
        str | int | float | bool | None,
    ] = Field(default_factory=dict)


class OrchestratorInput(BaseModel):
    """Input supplied to the Orchestrator Agent."""

    assessment_id: str = Field(min_length=1)
    proposal_document_id: str = Field(min_length=1)
    rfp_document_id: str | None = None

    requested_capabilities: list[str] = Field(
        default_factory=lambda: [
            "proposal_analysis",
            "vendor_research",
            "risk_report",
        ]
    )

    vendor_research_required: bool = True
    report_required: bool = True
    human_review_required: bool = True


class OrchestrationPlan(BaseModel):
    """Bounded specialist-agent execution plan."""

    assessment_id: str = Field(min_length=1)
    tasks: list[OrchestrationTask] = Field(min_length=1)
    maximum_steps: int = Field(default=12, ge=1, le=50)
    human_review_required: bool = True
    planning_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_plan(
        self,
    ) -> "OrchestrationPlan":
        """Validate task identity and dependency integrity."""

        task_ids = [task.task_id for task in self.tasks]

        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Orchestration task IDs must be unique.")

        available_task_ids = set(task_ids)

        for task in self.tasks:
            if task.task_id in task.depends_on:
                raise ValueError("An orchestration task cannot depend on itself.")

            missing_dependencies = set(task.depends_on) - available_task_ids

            if missing_dependencies:
                missing_text = ", ".join(sorted(missing_dependencies))

                raise ValueError(
                    f"Orchestration task references unknown dependencies: {missing_text}."
                )

        return self

    @property
    def task_count(self) -> int:
        """Return the number of planned tasks."""

        return len(self.tasks)

    @property
    def required_task_count(self) -> int:
        """Return the number of mandatory tasks."""

        return sum(1 for task in self.tasks if task.required)


class OrchestratorExecution(BaseModel):
    """Result returned by the deterministic orchestrator planner."""

    plan: OrchestrationPlan
    planner_version: str = Field(min_length=1)
    execution_time_ms: float = Field(ge=0)
