from functools import lru_cache

from app.repositories.assessment import InMemoryAssessmentRepository
from app.services.assessment_service import AssessmentService


@lru_cache
def get_assessment_repository() -> InMemoryAssessmentRepository:
    """Return the shared in-memory assessment repository."""

    return InMemoryAssessmentRepository()


@lru_cache
def get_assessment_service() -> AssessmentService:
    """Return the shared assessment service."""

    return AssessmentService(
        repository=get_assessment_repository(),
    )
