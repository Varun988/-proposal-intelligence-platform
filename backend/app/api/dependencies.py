from functools import lru_cache

from app.repositories.assessment import InMemoryAssessmentRepository
from app.services.assessment_execution_service import (
    AssessmentExecutionService,
    AssessmentWorkflowExecutorProtocol,
    UnavailableAssessmentWorkflowExecutor,
)
from app.services.assessment_service import AssessmentService


@lru_cache
def get_assessment_repository() -> InMemoryAssessmentRepository:
    """Return the shared in-memory assessment repository."""

    return InMemoryAssessmentRepository()


@lru_cache
def get_assessment_service() -> AssessmentService:
    """Return the shared assessment service."""

    return AssessmentService(repository=get_assessment_repository())


@lru_cache
def get_assessment_workflow_executor() -> AssessmentWorkflowExecutorProtocol:
    """Return the configured assessment workflow executor."""

    return UnavailableAssessmentWorkflowExecutor()


@lru_cache
def get_assessment_execution_service() -> AssessmentExecutionService:
    """Return the assessment execution service."""

    return AssessmentExecutionService(
        repository=get_assessment_repository(),
        workflow_executor=get_assessment_workflow_executor(),
    )
