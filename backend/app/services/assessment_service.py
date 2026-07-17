from app.core.exceptions import (
    AssessmentConflictError,
)
from app.repositories.assessment import (
    AssessmentRecord,
    AssessmentRepositoryProtocol,
)
from app.schemas.assessment import (
    AgentExecutionSummary,
    AssessmentCreateRequest,
    AssessmentCreateResponse,
    AssessmentLifecycleStatus,
    AssessmentResultsResponse,
    AssessmentStatusResponse,
    EvaluationSummary,
    create_assessment_id,
    utc_now,
)
from app.services.assessment_status_service import (
    map_workflow_status,
)
from app.workflows.state import WorkflowStatus


class AssessmentService:
    """Create and retrieve proposal assessment records."""

    def __init__(
        self,
        repository: AssessmentRepositoryProtocol,
    ) -> None:
        self._repository = repository

    async def create_assessment(
        self,
        request: AssessmentCreateRequest,
    ) -> AssessmentCreateResponse:
        """Create a new assessment without executing it."""

        assessment_id = create_assessment_id()
        timestamp = utc_now()

        if await self._repository.exists(
            assessment_id,
        ):
            raise AssessmentConflictError("Generated assessment ID already exists.")

        record = AssessmentRecord(
            assessment_id=assessment_id,
            request=request.model_copy(deep=True),
            lifecycle_status=(AssessmentLifecycleStatus.CREATED),
            workflow_status=WorkflowStatus.CREATED,
            created_at=timestamp,
            updated_at=timestamp,
        )

        created_record = await self._repository.create(
            record,
        )

        return self._to_create_response(
            created_record,
        )

    async def get_record(
        self,
        assessment_id: str,
    ) -> AssessmentRecord:
        """Retrieve an internal assessment record."""

        return await self._repository.get(
            assessment_id,
        )

    async def get_status(
        self,
        assessment_id: str,
    ) -> AssessmentStatusResponse:
        """Return a safe public assessment status."""

        record = await self._repository.get(
            assessment_id,
        )

        workflow_state = record.workflow_state

        if workflow_state is None:
            return AssessmentStatusResponse(
                assessment_id=record.assessment_id,
                lifecycle_status=record.lifecycle_status,
                workflow_status=record.workflow_status,
                current_step=0,
                maximum_steps=(record.request.maximum_workflow_steps),
                completed_agents=[],
                agent_executions=[],
                evaluations=[],
                human_review_required=(record.request.human_review_required),
                human_review_reason=None,
                error_count=0,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )

        return AssessmentStatusResponse(
            assessment_id=record.assessment_id,
            lifecycle_status=map_workflow_status(
                workflow_state.status,
            ),
            workflow_status=workflow_state.status,
            current_step=workflow_state.current_step,
            maximum_steps=workflow_state.maximum_steps,
            completed_agents=[
                *workflow_state.completed_agents,
            ],
            agent_executions=[
                AgentExecutionSummary(
                    agent_name=execution.agent_name,
                    succeeded=execution.succeeded,
                    tool_call_count=execution.tool_call_count,
                    execution_time_ms=(execution.execution_time_ms),
                    instruction_version=(execution.instruction_version),
                    error_message=execution.error_message,
                )
                for execution in workflow_state.agent_execution_records
            ],
            evaluations=[
                EvaluationSummary(
                    agent_name=evaluation.agent_name,
                    evaluation_id=evaluation.evaluation_id,
                    release_approved=(evaluation.release_approved),
                    overall_score=evaluation.overall_score,
                    blocking_gate_failure_count=(evaluation.blocking_gate_failure_count),
                )
                for evaluation in workflow_state.evaluation_records
            ],
            human_review_required=(workflow_state.human_review_required),
            human_review_reason=(workflow_state.human_review_reason),
            error_count=len(workflow_state.errors),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    async def get_results(
        self,
        assessment_id: str,
    ) -> AssessmentResultsResponse:
        """Return available specialist results and evaluations."""

        record = await self._repository.get(
            assessment_id,
        )

        workflow_state = record.workflow_state

        if workflow_state is None:
            return AssessmentResultsResponse(
                assessment_id=record.assessment_id,
                lifecycle_status=record.lifecycle_status,
                workflow_status=record.workflow_status,
                human_review_required=(record.request.human_review_required),
            )

        proposal_result = (
            workflow_state.proposal_analysis_execution.result
            if (workflow_state.proposal_analysis_execution is not None)
            else None
        )

        vendor_result = (
            workflow_state.vendor_research_execution.result
            if (workflow_state.vendor_research_execution is not None)
            else None
        )

        risk_result = (
            workflow_state.risk_report_execution.result
            if workflow_state.risk_report_execution is not None
            else None
        )

        return AssessmentResultsResponse(
            assessment_id=record.assessment_id,
            lifecycle_status=map_workflow_status(
                workflow_state.status,
            ),
            workflow_status=workflow_state.status,
            proposal_analysis=proposal_result,
            vendor_research=vendor_result,
            risk_report=risk_result,
            proposal_evaluation=(workflow_state.proposal_analysis_evaluation),
            vendor_evaluation=(workflow_state.vendor_research_evaluation),
            risk_report_evaluation=(workflow_state.risk_report_evaluation),
            human_review_required=(workflow_state.human_review_required),
            human_review_reason=(workflow_state.human_review_reason),
        )

    async def save_workflow_state(
        self,
        assessment_id: str,
        workflow_state: object,
    ) -> AssessmentRecord:
        """Persist a validated workflow state."""

        from app.workflows.state import (
            AssessmentWorkflowState,
        )

        validated_state = AssessmentWorkflowState.model_validate(
            workflow_state,
        )

        if validated_state.assessment_id != assessment_id:
            raise AssessmentConflictError(
                "Workflow state assessment ID does not match the repository record."
            )

        record = await self._repository.get(
            assessment_id,
        )

        updated_at = utc_now()

        updated_record = record.model_copy(
            update={
                "workflow_state": validated_state.model_copy(
                    deep=True,
                ),
                "workflow_status": validated_state.status,
                "lifecycle_status": map_workflow_status(
                    validated_state.status,
                ),
                "updated_at": updated_at,
            },
            deep=True,
        )

        return await self._repository.update(
            updated_record,
        )

    @staticmethod
    def _to_create_response(
        record: AssessmentRecord,
    ) -> AssessmentCreateResponse:
        """Convert an internal record to a create response."""

        return AssessmentCreateResponse(
            assessment_id=record.assessment_id,
            lifecycle_status=record.lifecycle_status,
            workflow_status=record.workflow_status,
            vendor_name=record.request.vendor_name,
            proposal_document_id=(record.request.proposal_document_id),
            rfp_document_id=(record.request.rfp_document_id),
            capabilities=[
                *record.request.capabilities,
            ],
            human_review_required=(record.request.human_review_required),
            created_at=record.created_at,
        )
