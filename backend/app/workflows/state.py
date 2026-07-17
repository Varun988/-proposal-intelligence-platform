from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.agents.orchestrator.schemas import (
    OrchestratorExecution,
    OrchestratorInput,
)
from app.agents.proposal_analysis.schemas import (
    ProposalAnalysisExecution,
    ProposalAnalysisInput,
)
from app.evaluation.schemas import AgentEvaluationReport


class WorkflowStatus(StrEnum):
    """Current lifecycle status of an assessment workflow."""

    CREATED = "created"
    INITIALIZING = "initializing"
    ORCHESTRATION_PENDING = "orchestration_pending"
    ORCHESTRATION_RUNNING = "orchestration_running"
    ORCHESTRATION_COMPLETED = "orchestration_completed"
    PROPOSAL_ANALYSIS_PENDING = "proposal_analysis_pending"
    PROPOSAL_ANALYSIS_RUNNING = "proposal_analysis_running"
    PROPOSAL_ANALYSIS_COMPLETED = "proposal_analysis_completed"
    EVALUATION_PENDING = "evaluation_pending"
    EVALUATION_RUNNING = "evaluation_running"
    EVALUATION_COMPLETED = "evaluation_completed"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    READY_FOR_NEXT_AGENT = "ready_for_next_agent"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowRoute(StrEnum):
    """Possible routing decisions made by the workflow."""

    RUN_ORCHESTRATION = "run_orchestration"
    RUN_PROPOSAL_ANALYSIS = "run_proposal_analysis"
    RUN_EVALUATION = "run_evaluation"
    REQUIRE_HUMAN_REVIEW = "require_human_review"
    CONTINUE_TO_NEXT_AGENT = "continue_to_next_agent"
    COMPLETE = "complete"
    FAIL = "fail"


class WorkflowEventType(StrEnum):
    """Types of auditable workflow events."""

    WORKFLOW_CREATED = "workflow_created"
    STATUS_CHANGED = "status_changed"
    ORCHESTRATION_STARTED = "orchestration_started"
    ORCHESTRATION_COMPLETED = "orchestration_completed"
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    EVALUATION_STARTED = "evaluation_started"
    EVALUATION_COMPLETED = "evaluation_completed"
    HUMAN_REVIEW_REQUESTED = "human_review_requested"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"


class WorkflowEvent(BaseModel):
    """One auditable state transition or workflow event."""

    event_type: WorkflowEventType
    status: WorkflowStatus
    message: str = Field(min_length=1)
    agent_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentExecutionRecord(BaseModel):
    """Summary of one agent execution within a workflow."""

    agent_name: str = Field(min_length=1)
    succeeded: bool
    tool_call_count: int = Field(ge=0)
    execution_time_ms: float = Field(ge=0)
    instruction_version: str = Field(min_length=1)
    error_message: str | None = None


class EvaluationRecord(BaseModel):
    """Summary of one agent evaluation run."""

    agent_name: str = Field(min_length=1)
    evaluation_id: str = Field(min_length=1)
    overall_score: float = Field(ge=0.0, le=1.0)
    release_approved: bool
    blocking_gate_failure_count: int = Field(ge=0)


class AssessmentWorkflowState(BaseModel):
    """Shared state used by the assessment LangGraph workflow."""

    assessment_id: str = Field(min_length=1)
    proposal_document_id: str = Field(min_length=1)
    rfp_document_id: str | None = None

    status: WorkflowStatus = WorkflowStatus.CREATED
    next_route: WorkflowRoute | None = None

    orchestrator_input: OrchestratorInput
    orchestrator_execution: OrchestratorExecution | None = None

    proposal_analysis_input: ProposalAnalysisInput
    proposal_analysis_execution: ProposalAnalysisExecution | None = None
    proposal_analysis_evaluation: AgentEvaluationReport | None = None

    agent_execution_records: list[AgentExecutionRecord] = Field(default_factory=list)
    evaluation_records: list[EvaluationRecord] = Field(default_factory=list)
    events: list[WorkflowEvent] = Field(default_factory=list)

    current_step: int = Field(default=0, ge=0)
    maximum_steps: int = Field(default=12, ge=1, le=50)
    retry_count: int = Field(default=0, ge=0)
    maximum_retries: int = Field(default=2, ge=0, le=5)

    human_review_required: bool = False
    human_review_reason: str | None = None

    completed_agents: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_identity_consistency(self) -> "AssessmentWorkflowState":
        """Ensure nested inputs match the workflow identity."""

        if self.orchestrator_input.assessment_id != self.assessment_id:
            raise ValueError("Orchestrator assessment ID must match the workflow assessment ID.")

        if self.orchestrator_input.proposal_document_id != self.proposal_document_id:
            raise ValueError(
                "Orchestrator proposal document ID must match the workflow proposal document ID."
            )

        if (
            self.rfp_document_id is not None
            and self.orchestrator_input.rfp_document_id != self.rfp_document_id
        ):
            raise ValueError(
                "Orchestrator RFP document ID must match the workflow RFP document ID."
            )

        if self.proposal_analysis_input.assessment_id != self.assessment_id:
            raise ValueError(
                "Proposal analysis assessment ID must match the workflow assessment ID."
            )

        if self.proposal_analysis_input.proposal_document_id != self.proposal_document_id:
            raise ValueError(
                "Proposal analysis document ID must match the workflow proposal document ID."
            )

        if (
            self.rfp_document_id is not None
            and self.proposal_analysis_input.rfp_document_id != self.rfp_document_id
        ):
            raise ValueError(
                "Proposal analysis RFP document ID must match the workflow RFP document ID."
            )

        return self

    @property
    def step_limit_reached(self) -> bool:
        """Return whether the workflow has reached its step limit."""

        return self.current_step >= self.maximum_steps

    @property
    def retry_limit_reached(self) -> bool:
        """Return whether the workflow has reached its retry limit."""

        return self.retry_count >= self.maximum_retries

    @property
    def proposal_analysis_passed(self) -> bool:
        """Return whether proposal analysis passed evaluation."""

        return bool(
            self.proposal_analysis_evaluation and self.proposal_analysis_evaluation.release_approved
        )

    @property
    def orchestration_completed(self) -> bool:
        """Return whether a validated orchestration plan exists."""

        return self.orchestrator_execution is not None
