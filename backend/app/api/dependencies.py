from functools import lru_cache

from app.core.config import get_settings
from app.documents.parsers import (
    PypdfPDFParser,
    Utf8TextDocumentParser,
)
from app.documents.registry import DocumentParserRegistry
from app.llm.providers.gemini import GeminiProvider
from app.rag.chunking import PageAwareDocumentChunker
from app.rag.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingProvider,
)
from app.rag.vector_store.faiss_store import (
    FaissVectorStore,
)
from app.repositories.assessment import InMemoryAssessmentRepository
from app.repositories.assessment_vector_index import (
    InMemoryAssessmentVectorIndexRegistry,
)
from app.repositories.document import (
    InMemoryDocumentRepository,
)
from app.repositories.document_chunk import (
    InMemoryDocumentChunkRepository,
)
from app.repositories.extracted_document import (
    InMemoryExtractedDocumentRepository,
)
from app.services.assessment_execution_service import (
    AssessmentExecutionService,
    AssessmentWorkflowExecutorProtocol,
    UnavailableAssessmentWorkflowExecutor,
)
from app.services.assessment_retrieval_context_service import (
    AssessmentRetrievalContextService,
)
from app.services.assessment_service import AssessmentService
from app.services.assessment_tool_context_service import (
    AssessmentToolContextService,
)
from app.services.document_chunk_processing_service import (
    DocumentChunkProcessingService,
)
from app.services.document_chunking_service import (
    DocumentChunkingService,
)
from app.services.document_extraction_service import (
    DocumentExtractionService,
)
from app.services.document_indexing_service import (
    DocumentIndexingService,
)
from app.services.document_pipeline_service import (
    DocumentPipelineService,
)
from app.services.document_processing_service import (
    DocumentProcessingService,
)
from app.services.document_service import DocumentService
from app.services.document_validation_service import (
    DocumentValidationService,
)
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.storage.document_storage import (
    InMemoryDocumentStorage,
)
from app.workflows.runtime_factory import (
    AssessmentWorkflowRuntimeFactory,
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
def get_document_repository() -> InMemoryDocumentRepository:
    """Return the shared document metadata repository."""

    return InMemoryDocumentRepository()


@lru_cache
def get_document_storage() -> InMemoryDocumentStorage:
    """Return the shared binary document storage."""

    return InMemoryDocumentStorage()


@lru_cache
def get_document_validation_service() -> DocumentValidationService:
    """Return the document validation service."""

    return DocumentValidationService()


@lru_cache
def get_document_service() -> DocumentService:
    """Return the shared document service."""

    return DocumentService(
        repository=get_document_repository(),
        storage=get_document_storage(),
        validation_service=(get_document_validation_service()),
    )


@lru_cache
def get_extracted_document_repository() -> InMemoryExtractedDocumentRepository:
    """Return the extracted-document repository."""

    return InMemoryExtractedDocumentRepository()


@lru_cache
def get_document_parser_registry() -> DocumentParserRegistry:
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
def get_document_extraction_service() -> DocumentExtractionService:
    """Return the path-based extraction service."""

    return DocumentExtractionService(
        registry=get_document_parser_registry(),
    )


@lru_cache
def get_document_processing_service() -> DocumentProcessingService:
    """Return the document processing service."""

    return DocumentProcessingService(
        document_repository=get_document_repository(),
        extracted_document_repository=(get_extracted_document_repository()),
        storage=get_document_storage(),
        extraction_service=(get_document_extraction_service()),
    )


@lru_cache
def get_document_chunk_repository() -> InMemoryDocumentChunkRepository:
    """Return the citation-ready chunk repository."""

    return InMemoryDocumentChunkRepository()


@lru_cache
def get_document_chunking_service() -> DocumentChunkingService:
    """Return the configured page-aware chunking service."""

    return DocumentChunkingService(
        chunker=PageAwareDocumentChunker(
            max_characters=1_500,
            overlap_characters=200,
        ),
    )


@lru_cache
def get_document_chunk_processing_service() -> DocumentChunkProcessingService:
    """Return the document chunk-processing service."""

    return DocumentChunkProcessingService(
        document_repository=get_document_repository(),
        extracted_document_repository=(get_extracted_document_repository()),
        chunk_repository=(get_document_chunk_repository()),
        chunking_service=get_document_chunking_service(),
    )


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """Return the configured local embedding service."""

    settings = get_settings()

    provider = SentenceTransformerEmbeddingProvider(
        model_name=settings.embedding_model,
        normalize_embeddings=(settings.normalize_embeddings),
    )

    return EmbeddingService(
        provider=provider,
    )


@lru_cache
def get_assessment_vector_index_registry() -> InMemoryAssessmentVectorIndexRegistry:
    """Return the assessment-isolated vector-index registry."""

    return InMemoryAssessmentVectorIndexRegistry(
        vector_store_factory=lambda dimension: FaissVectorStore(
            dimension=dimension,
            normalize_vectors=True,
        )
    )


@lru_cache
def get_document_indexing_service() -> DocumentIndexingService:
    """Return the document indexing service."""

    return DocumentIndexingService(
        document_repository=get_document_repository(),
        chunk_repository=get_document_chunk_repository(),
        index_registry=(get_assessment_vector_index_registry()),
        embedding_service=get_embedding_service(),
    )


@lru_cache
def get_document_pipeline_service() -> DocumentPipelineService:
    """Return the extraction, chunking, and indexing pipeline."""

    return DocumentPipelineService(
        extraction_service=(get_document_processing_service()),
        chunk_processing_service=(get_document_chunk_processing_service()),
        indexing_service=get_document_indexing_service(),
    )


@lru_cache
def get_assessment_retrieval_context_service() -> AssessmentRetrievalContextService:
    """Return the assessment-scoped retrieval context factory."""

    return AssessmentRetrievalContextService(
        embedding_service=get_embedding_service(),
        index_registry=(get_assessment_vector_index_registry()),
        candidate_limit=20,
        final_limit=5,
    )


@lru_cache
def get_assessment_tool_context_service() -> AssessmentToolContextService:
    """Return the bounded specialist-tool context factory."""

    return AssessmentToolContextService(
        retrieval_context_service=(get_assessment_retrieval_context_service())
    )


def create_assessment_llm_service() -> LLMService:
    """Create a fresh bounded LLM service for one workflow."""

    settings = get_settings()

    provider = GeminiProvider(
        api_key=settings.gemini_api_key,
        model_name=settings.llm_model,
    )

    return LLMService(
        provider=provider,
        max_calls_per_assessment=3,
    )


@lru_cache
def get_assessment_runtime_factory() -> AssessmentWorkflowRuntimeFactory:
    """Return the assessment-specific workflow runtime factory."""

    return AssessmentWorkflowRuntimeFactory(
        tool_context_service=(get_assessment_tool_context_service()),
        llm_service_factory=create_assessment_llm_service,
    )
