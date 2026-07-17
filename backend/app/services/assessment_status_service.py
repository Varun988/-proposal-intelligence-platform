from app.schemas.assessment import (
    AssessmentLifecycleStatus,
)
from app.workflows.state import WorkflowStatus


def map_workflow_status(
    workflow_status: WorkflowStatus,
) -> AssessmentLifecycleStatus:
    """Map internal workflow status to public lifecycle status."""

    if workflow_status is WorkflowStatus.CREATED:
        return AssessmentLifecycleStatus.CREATED

    if workflow_status is WorkflowStatus.HUMAN_REVIEW_REQUIRED:
        return AssessmentLifecycleStatus.HUMAN_REVIEW_REQUIRED

    if workflow_status is WorkflowStatus.COMPLETED:
        return AssessmentLifecycleStatus.COMPLETED

    if workflow_status is WorkflowStatus.FAILED:
        return AssessmentLifecycleStatus.FAILED

    return AssessmentLifecycleStatus.RUNNING
