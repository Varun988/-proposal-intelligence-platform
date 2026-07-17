import pytest
from app.repositories.assessment import (
    InMemoryAssessmentRepository,
)
from app.services.assessment_service import (
    AssessmentService,
)

from app.schemas.assessment import (
    AssessmentCreateRequest,
    AssessmentLifecycleStatus,
)
from app.workflows.state import WorkflowStatus


def create_service() -> AssessmentService:
    """Create an isolated assessment service."""

    return AssessmentService(
        repository=InMemoryAssessmentRepository(),
    )


@pytest.mark.asyncio
async def test_service_creates_assessment() -> None:
    service = create_service()

    response = await service.create_assessment(
        AssessmentCreateRequest(
            vendor_name="Example Digital Services",
            proposal_document_id="proposal-001",
        )
    )

    assert response.assessment_id.startswith("assessment-")
    assert response.lifecycle_status is AssessmentLifecycleStatus.CREATED
    assert response.workflow_status is WorkflowStatus.CREATED
    assert response.vendor_name == "Example Digital Services"
    assert response.human_review_required is True


@pytest.mark.asyncio
async def test_service_returns_created_status() -> None:
    service = create_service()

    created = await service.create_assessment(
        AssessmentCreateRequest(
            vendor_name="Example Digital Services",
            proposal_document_id="proposal-001",
        )
    )

    status = await service.get_status(
        created.assessment_id,
    )

    assert status.assessment_id == (created.assessment_id)
    assert status.lifecycle_status is AssessmentLifecycleStatus.CREATED
    assert status.workflow_status is WorkflowStatus.CREATED
    assert status.current_step == 0
    assert status.maximum_steps == 12
    assert status.completed_agents == []
    assert status.agent_executions == []
    assert status.evaluations == []
    assert status.human_review_required is True
    assert status.error_count == 0


@pytest.mark.asyncio
async def test_service_returns_empty_created_results() -> None:
    service = create_service()

    created = await service.create_assessment(
        AssessmentCreateRequest(
            vendor_name="Example Digital Services",
            proposal_document_id="proposal-001",
        )
    )

    results = await service.get_results(
        created.assessment_id,
    )

    assert results.proposal_analysis is None
    assert results.vendor_research is None
    assert results.risk_report is None
    assert results.proposal_evaluation is None
    assert results.vendor_evaluation is None
    assert results.risk_report_evaluation is None
    assert results.human_review_required is True
