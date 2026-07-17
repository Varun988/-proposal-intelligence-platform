from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from app.agents.proposal_analysis.schemas import (
    ProposalAnalysisResult,
)
from app.agents.risk_report.schemas import RiskReportResult
from app.agents.vendor_research.schemas import (
    VendorResearchResult,
)
from app.evaluation.schemas import AgentEvaluationReport
from app.workflows.state import WorkflowStatus


class AssessmentLifecycleStatus(StrEnum):
    """Externally visible assessment lifecycle status."""

    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    COMPLETED = "completed"
    FAILED = "failed"


class AssessmentCapability(StrEnum):
    """Specialist capabilities requested for an assessment."""

    PROPOSAL_ANALYSIS = "proposal_analysis"
    RISK_REPORT = "risk_report"
    VENDOR_RESEARCH = "vendor_research"


class AssessmentCreateRequest(BaseModel):
    """Request used to create a proposal assessment."""

    vendor_name: str = Field(
        min_length=1,
        max_length=200,
    )
    proposal_document_id: str = Field(
        min_length=1,
        max_length=200,
    )
    rfp_document_id: str | None = Field(
        default=None,
        max_length=200,
    )

    capabilities: list[AssessmentCapability] = Field(
        default_factory=lambda: [
            AssessmentCapability.PROPOSAL_ANALYSIS,
            AssessmentCapability.VENDOR_RESEARCH,
            AssessmentCapability.RISK_REPORT,
        ],
        min_length=1,
    )

    proposal_requirements: list[str] = Field(
        default_factory=list,
    )
    proposal_analysis_objectives: list[str] = Field(
        default_factory=list,
    )
    vendor_research_objectives: list[str] = Field(
        default_factory=list,
    )
    report_objectives: list[str] = Field(
        default_factory=list,
    )

    stale_vendor_evidence_after_days: int = Field(
        default=365,
        ge=1,
        le=3_650,
    )
    maximum_workflow_steps: int = Field(
        default=12,
        ge=1,
        le=50,
    )
    maximum_retries: int = Field(
        default=2,
        ge=0,
        le=5,
    )
    human_review_required: bool = True

    @model_validator(mode="after")
    def validate_capability_dependencies(
        self,
    ) -> "AssessmentCreateRequest":
        """Validate safe specialist-capability dependencies."""

        capability_set = set(self.capabilities)

        if (
            AssessmentCapability.RISK_REPORT in capability_set
            and AssessmentCapability.PROPOSAL_ANALYSIS not in capability_set
        ):
            raise ValueError("Risk reporting requires proposal analysis.")

        if (
            AssessmentCapability.VENDOR_RESEARCH in capability_set
            and AssessmentCapability.PROPOSAL_ANALYSIS not in capability_set
        ):
            raise ValueError("Vendor research requires proposal analysis.")

        if not self.human_review_required:
            raise ValueError("Assessment creation must require human review.")

        return self


class AssessmentCreateResponse(BaseModel):
    """Response returned after creating an assessment."""

    assessment_id: str = Field(min_length=1)
    lifecycle_status: AssessmentLifecycleStatus
    workflow_status: WorkflowStatus
    vendor_name: str = Field(min_length=1)
    proposal_document_id: str = Field(min_length=1)
    rfp_document_id: str | None = None
    capabilities: list[AssessmentCapability]
    human_review_required: bool
    created_at: datetime


class AssessmentExecuteResponse(BaseModel):
    """Response returned after accepting an execution request."""

    assessment_id: str = Field(min_length=1)
    lifecycle_status: AssessmentLifecycleStatus
    workflow_status: WorkflowStatus
    execution_accepted: bool
    message: str = Field(min_length=1)


class AgentExecutionSummary(BaseModel):
    """Safe externally visible summary of one agent execution."""

    agent_name: str = Field(min_length=1)
    succeeded: bool
    tool_call_count: int = Field(ge=0)
    execution_time_ms: float = Field(ge=0)
    instruction_version: str = Field(min_length=1)
    error_message: str | None = None


class EvaluationSummary(BaseModel):
    """Safe externally visible summary of one evaluation run."""

    agent_name: str = Field(min_length=1)
    evaluation_id: str = Field(min_length=1)
    release_approved: bool
    overall_score: float = Field(ge=0.0, le=1.0)
    blocking_gate_failure_count: int = Field(ge=0)


class AssessmentStatusResponse(BaseModel):
    """Current status of one assessment workflow."""

    assessment_id: str = Field(min_length=1)
    lifecycle_status: AssessmentLifecycleStatus
    workflow_status: WorkflowStatus

    current_step: int = Field(ge=0)
    maximum_steps: int = Field(ge=1)

    completed_agents: list[str] = Field(
        default_factory=list,
    )
    agent_executions: list[AgentExecutionSummary] = Field(
        default_factory=list,
    )
    evaluations: list[EvaluationSummary] = Field(
        default_factory=list,
    )

    human_review_required: bool
    human_review_reason: str | None = None
    error_count: int = Field(ge=0)

    created_at: datetime
    updated_at: datetime


class AssessmentResultsResponse(BaseModel):
    """Consolidated outputs from a completed assessment."""

    assessment_id: str = Field(min_length=1)
    lifecycle_status: AssessmentLifecycleStatus
    workflow_status: WorkflowStatus

    proposal_analysis: ProposalAnalysisResult | None = None
    vendor_research: VendorResearchResult | None = None
    risk_report: RiskReportResult | None = None

    proposal_evaluation: AgentEvaluationReport | None = None
    vendor_evaluation: AgentEvaluationReport | None = None
    risk_report_evaluation: AgentEvaluationReport | None = None

    human_review_required: bool
    human_review_reason: str | None = None


class AssessmentErrorResponse(BaseModel):
    """Safe error response returned by assessment endpoints."""

    error_code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    assessment_id: str | None = None
    details: dict[
        str,
        str | int | float | bool | None,
    ] = Field(default_factory=dict)


def create_assessment_id() -> str:
    """Create a unique assessment identifier."""

    return f"assessment-{uuid4()}"


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""

    return datetime.now(UTC)
