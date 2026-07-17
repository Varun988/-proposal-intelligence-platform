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
from app.documents.parsers import (
    PypdfPDFParser,
    Utf8TextDocumentParser,
)
from app.documents.registry import DocumentParserRegistry
from app.repositories.extracted_document import (
    InMemoryExtractedDocumentRepository,
)
from app.services.document_extraction_service import (
    DocumentExtractionService,
)
from app.services.document_processing_service import (
    DocumentProcessingService,
)
from app.rag.chunking import PageAwareDocumentChunker
from app.repositories.document_chunk import (
    InMemoryDocumentChunkRepository,
)
from app.services.document_chunk_processing_service import (
    DocumentChunkProcessingService,
)
from app.services.document_chunking_service import (
    DocumentChunkingService,
)
from app.services.document_pipeline_service import (
    DocumentPipelineService,
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

@lru_cache
def get_extracted_document_repository(
) -> InMemoryExtractedDocumentRepository:
    """Return the extracted-document repository."""

    return InMemoryExtractedDocumentRepository()


@lru_cache
def get_document_parser_registry(
) -> DocumentParserRegistry:
    """Return the configured document parser registry."""

    registry = DocumentParserRegistry()

    registry.register(
        PypdfPDFParser(),
    )
    registry.register(
        Utf8TextDocumentParser(),
    )

    return registry


@lru_cache
def get_document_extraction_service(
) -> DocumentExtractionService:
    """Return the path-based extraction service."""

    return DocumentExtractionService(
        registry=get_document_parser_registry(),
    )


@lru_cache
def get_document_processing_service(
) -> DocumentProcessingService:
    """Return the document processing service."""

    return DocumentProcessingService(
        document_repository=get_document_repository(),
        extracted_document_repository=(
            get_extracted_document_repository()
        ),
        storage=get_document_storage(),
        extraction_service=(
            get_document_extraction_service()
        ),
    )

@lru_cache
def get_document_chunk_repository(
) -> InMemoryDocumentChunkRepository:
    """Return the citation-ready chunk repository."""

    return InMemoryDocumentChunkRepository()


@lru_cache
def get_document_chunking_service(
) -> DocumentChunkingService:
    """Return the configured page-aware chunking service."""

    return DocumentChunkingService(
        chunker=PageAwareDocumentChunker(
            max_characters=1_500,
            overlap_characters=200,
        ),
    )


@lru_cache
def get_document_chunk_processing_service(
) -> DocumentChunkProcessingService:
    """Return the document chunk-processing service."""

    return DocumentChunkProcessingService(
        document_repository=get_document_repository(),
        extracted_document_repository=(
            get_extracted_document_repository()
        ),
        chunk_repository=(
            get_document_chunk_repository()
        ),
        chunking_service=get_document_chunking_service(),
    )


@lru_cache
def get_document_pipeline_service(
) -> DocumentPipelineService:
    """Return the extraction and chunking pipeline."""

    return DocumentPipelineService(
        extraction_service=(
            get_document_processing_service()
        ),
        chunk_processing_service=(
            get_document_chunk_processing_service()
        ),
    )