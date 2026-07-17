from typing import Protocol

from app.agents.orchestrator.schemas import OrchestratorInput
from app.agents.proposal_analysis.schemas import (
    FindingConfidence,
    ProposalAnalysisInput,
    ProposalAnalysisResult,
    ProposalSummary,
)
from app.agents.risk_report.schemas import RiskReportInput
from app.agents.vendor_research.schemas import VendorResearchInput
from app.core.exceptions import AssessmentExecutionError
from app.repositories.assessment import (
    AssessmentRecord,
    AssessmentRepositoryProtocol,
)
from app.schemas.assessment import (
    AssessmentCapability,
    AssessmentExecuteResponse,
    AssessmentLifecycleStatus,
    utc_now,
)
from app.services.assessment_status_service import map_workflow_status
from app.workflows.state import AssessmentWorkflowState, WorkflowStatus


class AssessmentWorkflowExecutorProtocol(Protocol):
    """Execution contract for an assessment workflow."""

    async def execute(
        self,
        state: AssessmentWorkflowState,
    ) -> AssessmentWorkflowState:
        """Execute a workflow and return its final state."""


class UnavailableAssessmentWorkflowExecutor:
    """Executor used until the live workflow factory is configured."""

    async def execute(
        self,
        state: AssessmentWorkflowState,
    ) -> AssessmentWorkflowState:
        """Reject execution when no live workflow is configured."""

        raise AssessmentExecutionError("The live assessment workflow executor is not configured.")


class AssessmentExecutionService:
    """Queue and execute assessment workflows."""

    def __init__(
        self,
        repository: AssessmentRepositoryProtocol,
        workflow_executor: AssessmentWorkflowExecutorProtocol,
    ) -> None:
        self._repository = repository
        self._workflow_executor = workflow_executor

    async def request_execution(
        self,
        assessment_id: str,
    ) -> AssessmentExecuteResponse:
        """Atomically queue an assessment for execution."""

        record = await self._repository.claim_execution(
            assessment_id=assessment_id,
            updated_at=utc_now(),
        )
        return AssessmentExecuteResponse(
            assessment_id=record.assessment_id,
            lifecycle_status=record.lifecycle_status,
            workflow_status=record.workflow_status,
            execution_accepted=True,
            message="Assessment execution was accepted and queued.",
        )

    async def execute_assessment(self, assessment_id: str) -> None:
        """Execute and persist one assessment workflow."""

        record = await self._repository.get(assessment_id)
        initial_state = self._build_initial_state(record)
        await self._mark_running(record=record, state=initial_state)

        try:
            result = await self._workflow_executor.execute(initial_state.model_copy(deep=True))
            final_state = AssessmentWorkflowState.model_validate(result)
            if final_state.assessment_id != assessment_id:
                raise AssessmentExecutionError(
                    "Workflow result assessment ID does not match the requested assessment."
                )
            await self._save_final_state(
                assessment_id=assessment_id,
                final_state=final_state,
            )
        except Exception as error:
            await self._save_failed_state(
                assessment_id=assessment_id,
                initial_state=initial_state,
                error=error,
            )

    @staticmethod
    def _build_initial_state(
        record: AssessmentRecord,
    ) -> AssessmentWorkflowState:
        """Build workflow state from the stored API request."""

        request = record.request
        capabilities = set(request.capabilities)
        vendor_research_required = AssessmentCapability.VENDOR_RESEARCH in capabilities
        report_required = AssessmentCapability.RISK_REPORT in capabilities

        proposal_objectives = request.proposal_analysis_objectives or [
            "scope and delivery timeline",
            "pricing, assumptions, and exclusions",
            "staffing, support, and security controls",
        ]
        vendor_objectives = request.vendor_research_objectives or [
            "company profile and ownership",
            "financial information",
            "security posture and certifications",
            "compliance information",
            "reputation and relevant adverse events",
        ]
        report_objectives = request.report_objectives or [
            "summarize validated proposal findings",
            "summarize validated vendor research",
            "identify material cross-agent risks",
            "provide mitigations and clarification questions",
            "prepare reviewer and executive reports",
        ]

        placeholder_proposal_result = ProposalAnalysisResult(
            assessment_id=record.assessment_id,
            proposal_document_id=request.proposal_document_id,
            summary=ProposalSummary(),
            executive_summary=(
                "Placeholder input that will be replaced by validated Proposal Analysis output."
            ),
            overall_confidence=FindingConfidence.LOW,
            human_review_required=True,
            analysis_limitations=["Placeholder specialist output; not used as final evidence."],
        )

        vendor_input = None
        if vendor_research_required:
            vendor_input = VendorResearchInput(
                assessment_id=record.assessment_id,
                vendor_name=request.vendor_name,
                proposal_document_id=request.proposal_document_id,
                research_objectives=list(vendor_objectives),
                stale_after_days=request.stale_vendor_evidence_after_days,
            )

        risk_input = None
        if report_required:
            risk_input = RiskReportInput(
                assessment_id=record.assessment_id,
                proposal_document_id=request.proposal_document_id,
                vendor_name=request.vendor_name,
                proposal_analysis=placeholder_proposal_result,
                report_objectives=list(report_objectives),
                human_review_required=True,
            )

        return AssessmentWorkflowState(
            assessment_id=record.assessment_id,
            proposal_document_id=request.proposal_document_id,
            rfp_document_id=request.rfp_document_id,
            status=WorkflowStatus.INITIALIZING,
            orchestrator_input=OrchestratorInput(
                assessment_id=record.assessment_id,
                proposal_document_id=request.proposal_document_id,
                rfp_document_id=request.rfp_document_id,
                vendor_research_required=vendor_research_required,
                report_required=report_required,
                human_review_required=True,
            ),
            proposal_analysis_input=ProposalAnalysisInput(
                assessment_id=record.assessment_id,
                proposal_document_id=request.proposal_document_id,
                rfp_document_id=request.rfp_document_id,
                analysis_objectives=list(proposal_objectives),
                requirements=list(request.proposal_requirements),
            ),
            vendor_research_input=vendor_input,
            risk_report_input=risk_input,
            maximum_steps=request.maximum_workflow_steps,
            maximum_retries=request.maximum_retries,
            human_review_required=False,
        )

    async def _mark_running(
        self,
        record: AssessmentRecord,
        state: AssessmentWorkflowState,
    ) -> None:
        """Persist the initial running state."""

        timestamp = utc_now()
        updated_record = record.model_copy(
            update={
                "lifecycle_status": AssessmentLifecycleStatus.RUNNING,
                "workflow_status": state.status,
                "workflow_state": state.model_copy(deep=True),
                "execution_started_at": timestamp,
                "updated_at": timestamp,
            },
            deep=True,
        )
        await self._repository.update(updated_record)

    async def _save_final_state(
        self,
        assessment_id: str,
        final_state: AssessmentWorkflowState,
    ) -> None:
        """Persist a successfully returned workflow state."""

        record = await self._repository.get(assessment_id)
        timestamp = utc_now()
        updated_record = record.model_copy(
            update={
                "workflow_state": final_state.model_copy(deep=True),
                "workflow_status": final_state.status,
                "lifecycle_status": map_workflow_status(final_state.status),
                "execution_completed_at": timestamp,
                "updated_at": timestamp,
            },
            deep=True,
        )
        await self._repository.update(updated_record)

    async def _save_failed_state(
        self,
        assessment_id: str,
        initial_state: AssessmentWorkflowState,
        error: Exception,
    ) -> None:
        """Persist a safe failed workflow state."""

        record = await self._repository.get(assessment_id)
        error_message = f"Assessment workflow execution failed: {type(error).__name__}."
        safe_error_detail = str(error).strip()
        if safe_error_detail:
            error_message = f"{error_message} {safe_error_detail}"

        failed_state = initial_state.model_copy(
            update={
                "status": WorkflowStatus.FAILED,
                "next_route": None,
                "human_review_required": True,
                "human_review_reason": error_message,
                "errors": initial_state.errors + [error_message],
            },
            deep=True,
        )
        timestamp = utc_now()
        updated_record = record.model_copy(
            update={
                "workflow_state": failed_state,
                "workflow_status": WorkflowStatus.FAILED,
                "lifecycle_status": AssessmentLifecycleStatus.FAILED,
                "execution_completed_at": timestamp,
                "updated_at": timestamp,
            },
            deep=True,
        )
        await self._repository.update(updated_record)
