import pytest

from app.core.exceptions import AssessmentConflictError
from app.repositories.assessment import InMemoryAssessmentRepository
from app.schemas.assessment import (
    AssessmentCreateRequest,
    AssessmentLifecycleStatus,
)
from app.services.assessment_execution_service import AssessmentExecutionService
from app.services.assessment_service import AssessmentService
from app.workflows.state import WorkflowStatus
from tests.assessment_execution_fakes import FakeAssessmentWorkflowExecutor


def create_services(
    executor: FakeAssessmentWorkflowExecutor,
) -> tuple[AssessmentService, AssessmentExecutionService]:
    """Create services sharing one repository."""

    repository = InMemoryAssessmentRepository()
    return (
        AssessmentService(repository=repository),
        AssessmentExecutionService(
            repository=repository,
            workflow_executor=executor,
        ),
    )


async def create_assessment(service: AssessmentService) -> str:
    """Create an assessment and return its ID."""

    response = await service.create_assessment(
        AssessmentCreateRequest(
            vendor_name="Example Digital Services",
            proposal_document_id="proposal-001",
        )
    )
    return response.assessment_id


@pytest.mark.asyncio
async def test_execution_request_is_queued() -> None:
    executor = FakeAssessmentWorkflowExecutor()
    assessment_service, execution_service = create_services(executor)
    assessment_id = await create_assessment(assessment_service)

    response = await execution_service.request_execution(assessment_id)

    assert response.execution_accepted is True
    assert response.lifecycle_status is AssessmentLifecycleStatus.QUEUED


@pytest.mark.asyncio
async def test_execution_service_completes_workflow() -> None:
    executor = FakeAssessmentWorkflowExecutor()
    assessment_service, execution_service = create_services(executor)
    assessment_id = await create_assessment(assessment_service)

    await execution_service.request_execution(assessment_id)
    await execution_service.execute_assessment(assessment_id)
    status = await assessment_service.get_status(assessment_id)

    assert status.lifecycle_status is AssessmentLifecycleStatus.COMPLETED
    assert status.workflow_status is WorkflowStatus.COMPLETED
    assert status.current_step == 10
    assert status.human_review_required is True
    assert len(executor.received_states) == 1


@pytest.mark.asyncio
async def test_execution_service_persists_human_review() -> None:
    executor = FakeAssessmentWorkflowExecutor(final_status=WorkflowStatus.HUMAN_REVIEW_REQUIRED)
    assessment_service, execution_service = create_services(executor)
    assessment_id = await create_assessment(assessment_service)

    await execution_service.request_execution(assessment_id)
    await execution_service.execute_assessment(assessment_id)
    status = await assessment_service.get_status(assessment_id)

    assert status.lifecycle_status is AssessmentLifecycleStatus.HUMAN_REVIEW_REQUIRED
    assert status.workflow_status is WorkflowStatus.HUMAN_REVIEW_REQUIRED
    assert status.human_review_reason is not None


@pytest.mark.asyncio
async def test_execution_service_persists_failure() -> None:
    executor = FakeAssessmentWorkflowExecutor(should_fail=True)
    assessment_service, execution_service = create_services(executor)
    assessment_id = await create_assessment(assessment_service)

    await execution_service.request_execution(assessment_id)
    await execution_service.execute_assessment(assessment_id)
    status = await assessment_service.get_status(assessment_id)

    assert status.lifecycle_status is AssessmentLifecycleStatus.FAILED
    assert status.workflow_status is WorkflowStatus.FAILED
    assert status.human_review_required is True
    assert status.error_count == 1


@pytest.mark.asyncio
async def test_execution_request_rejects_duplicate() -> None:
    executor = FakeAssessmentWorkflowExecutor()
    assessment_service, execution_service = create_services(executor)
    assessment_id = await create_assessment(assessment_service)

    await execution_service.request_execution(assessment_id)

    with pytest.raises(
        AssessmentConflictError,
        match="already been requested",
    ):
        await execution_service.request_execution(assessment_id)


@pytest.mark.asyncio
async def test_initial_workflow_state_is_not_preemptively_escalated(
) -> None:
    executor = FakeAssessmentWorkflowExecutor()

    assessment_service, execution_service = (
        create_services(executor)
    )

    created = await assessment_service.create_assessment(
        AssessmentCreateRequest(
            vendor_name="Example Digital Services",
            proposal_document_id="proposal-001",
        )
    )

    await execution_service.request_execution(
        created.assessment_id,
    )

    await execution_service.execute_assessment(
        created.assessment_id,
    )

    assert len(executor.received_states) == 1

    initial_state = executor.received_states[0]

    assert initial_state.human_review_required is False

    assert (
        initial_state
        .orchestrator_input
        .human_review_required
        is True
    )

    assert initial_state.risk_report_input is not None

    assert (
        initial_state
        .risk_report_input
        .human_review_required
        is True
    )