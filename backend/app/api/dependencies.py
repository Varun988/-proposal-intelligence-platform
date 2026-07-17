from functools import lru_cache

from app.repositories.assessment import InMemoryAssessmentRepository
from app.services.assessment_execution_service import (
    AssessmentExecutionService,
    AssessmentWorkflowExecutorProtocol,
    UnavailableAssessmentWorkflowExecutor,
)
from app.services.assessment_service import AssessmentService
from app.repositories.document import (
    InMemoryDocumentRepository,
)
from app.services.document_service import DocumentService
from app.services.document_validation_service import (
    DocumentValidationService,
)
from app.storage.document_storage import (
    InMemoryDocumentStorage,
)

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


@lru_cache
def get_document_repository(
) -> InMemoryDocumentRepository:
    """Return the shared document metadata repository."""

    return InMemoryDocumentRepository()


@lru_cache
def get_document_storage(
) -> InMemoryDocumentStorage:
    """Return the shared binary document storage."""

    return InMemoryDocumentStorage()


@lru_cache
def get_document_validation_service(
) -> DocumentValidationService:
    """Return the document validation service."""

    return DocumentValidationService()


@lru_cache
def get_document_service() -> DocumentService:
    """Return the shared document service."""

    return DocumentService(
        repository=get_document_repository(),
        storage=get_document_storage(),
        validation_service=(
            get_document_validation_service()
        ),
    )