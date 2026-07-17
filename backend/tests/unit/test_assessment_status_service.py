import pytest

from app.schemas.assessment import (
    AssessmentLifecycleStatus,
)
from app.services.assessment_status_service import (
    map_workflow_status,
)
from app.workflows.state import WorkflowStatus


@pytest.mark.parametrize(
    (
        "workflow_status",
        "expected_lifecycle_status",
    ),
    [
        (
            WorkflowStatus.CREATED,
            AssessmentLifecycleStatus.CREATED,
        ),
        (
            WorkflowStatus.ORCHESTRATION_RUNNING,
            AssessmentLifecycleStatus.RUNNING,
        ),
        (
            WorkflowStatus.PROPOSAL_ANALYSIS_RUNNING,
            AssessmentLifecycleStatus.RUNNING,
        ),
        (
            WorkflowStatus.VENDOR_RESEARCH_RUNNING,
            AssessmentLifecycleStatus.RUNNING,
        ),
        (
            WorkflowStatus.RISK_REPORT_RUNNING,
            AssessmentLifecycleStatus.RUNNING,
        ),
        (
            WorkflowStatus.HUMAN_REVIEW_REQUIRED,
            AssessmentLifecycleStatus.HUMAN_REVIEW_REQUIRED,
        ),
        (
            WorkflowStatus.COMPLETED,
            AssessmentLifecycleStatus.COMPLETED,
        ),
        (
            WorkflowStatus.FAILED,
            AssessmentLifecycleStatus.FAILED,
        ),
    ],
)
def test_map_workflow_status(
    workflow_status: WorkflowStatus,
    expected_lifecycle_status: AssessmentLifecycleStatus,
) -> None:
    result = map_workflow_status(
        workflow_status,
    )

    assert result is expected_lifecycle_status
