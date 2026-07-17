import pytest

from app.core.exceptions import DocumentNotFoundError
from app.rag.vector_store.faiss_store import FaissVectorStore
from app.repositories.assessment_vector_index import (
    InMemoryAssessmentVectorIndexRegistry,
)
from app.schemas.chunk import ChunkCitation, DocumentChunk
from app.services.assessment_retrieval_context_service import (
    AssessmentRetrievalContextService,
)
from app.services.embedding_service import EmbeddingService
from tests.embedding_fakes import FakeEmbeddingProvider


def create_chunk(
    assessment_id: str,
    document_id: str,
    chunk_id: str,
    text: str,
) -> DocumentChunk:
    """Create one assessment-associated chunk."""

    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        text=text,
        page_number=1,
        page_chunk_index=0,
        document_chunk_index=0,
        citation=ChunkCitation(
            document_id=document_id,
            file_name=f"{document_id}.txt",
            page_number=1,
            checksum_sha256="a" * 64,
        ),
        metadata={
            "assessment_id": assessment_id,
            "document_purpose": "proposal",
        },
    )


def create_context() -> tuple[
    AssessmentRetrievalContextService,
    InMemoryAssessmentVectorIndexRegistry,
    EmbeddingService,
]:
    """Create an isolated retrieval context with fake embeddings."""

    embedding_service = EmbeddingService(provider=FakeEmbeddingProvider(dimension=3))
    registry = InMemoryAssessmentVectorIndexRegistry(
        vector_store_factory=lambda dimension: FaissVectorStore(dimension=dimension)
    )
    context = AssessmentRetrievalContextService(
        embedding_service=embedding_service,
        index_registry=registry,
        candidate_limit=10,
        final_limit=5,
    )
    return context, registry, embedding_service


async def index_document(
    registry: InMemoryAssessmentVectorIndexRegistry,
    embedding_service: EmbeddingService,
    assessment_id: str,
    document_id: str,
    chunk_id: str,
    text: str,
) -> None:
    """Embed and index one document for an assessment."""

    chunk = create_chunk(
        assessment_id=assessment_id,
        document_id=document_id,
        chunk_id=chunk_id,
        text=text,
    )
    embedding_result = embedding_service.embed_chunks([chunk])

    await registry.add_document(
        assessment_id=assessment_id,
        document_id=document_id,
        items=embedding_result.items,
        embedding_provider=embedding_result.provider_name,
        embedding_model=embedding_result.model_name,
        vector_dimension=embedding_result.dimension,
    )


@pytest.mark.asyncio
async def test_context_retrieves_only_requested_assessment() -> None:
    context, registry, embedding_service = create_context()

    await index_document(
        registry=registry,
        embedding_service=embedding_service,
        assessment_id="assessment-001",
        document_id="document-001",
        chunk_id="chunk-001",
        text="Implementation timeline is twelve months.",
    )
    await index_document(
        registry=registry,
        embedding_service=embedding_service,
        assessment_id="assessment-002",
        document_id="document-002",
        chunk_id="chunk-002",
        text="A different assessment contains confidential pricing.",
    )

    retrieval_service = await context.create_retrieval_service("assessment-001")
    response = retrieval_service.retrieve("implementation timeline")

    assert response.candidates
    assert {candidate.chunk.document_id for candidate in response.candidates} == {"document-001"}
    assert all(
        candidate.chunk.metadata["assessment_id"] == "assessment-001"
        for candidate in response.candidates
    )


@pytest.mark.asyncio
async def test_context_rejects_unknown_assessment() -> None:
    context, _, _ = create_context()

    with pytest.raises(DocumentNotFoundError, match="not found"):
        await context.create_retrieval_service("assessment-missing")


@pytest.mark.asyncio
async def test_context_rejects_empty_assessment_id() -> None:
    context, _, _ = create_context()

    with pytest.raises(ValueError, match="Assessment ID is required"):
        await context.create_retrieval_service("   ")


@pytest.mark.asyncio
async def test_context_preserves_explicit_pipeline_limits() -> None:
    context, registry, embedding_service = create_context()

    await index_document(
        registry=registry,
        embedding_service=embedding_service,
        assessment_id="assessment-001",
        document_id="document-001",
        chunk_id="chunk-001",
        text="Synthetic proposal implementation timeline.",
    )

    retrieval_service = await context.create_retrieval_service("assessment-001")

    assert retrieval_service.candidate_limit == 10
    assert retrieval_service.final_limit == 5


@pytest.mark.asyncio
async def test_context_rejects_dimension_mismatch() -> None:
    embedding_service = EmbeddingService(provider=FakeEmbeddingProvider(dimension=4))
    registry = InMemoryAssessmentVectorIndexRegistry(
        vector_store_factory=lambda dimension: FaissVectorStore(dimension=dimension)
    )

    three_dimensional_service = EmbeddingService(provider=FakeEmbeddingProvider(dimension=3))
    await index_document(
        registry=registry,
        embedding_service=three_dimensional_service,
        assessment_id="assessment-001",
        document_id="document-001",
        chunk_id="chunk-001",
        text="Synthetic proposal content.",
    )

    context = AssessmentRetrievalContextService(
        embedding_service=embedding_service,
        index_registry=registry,
    )

    with pytest.raises(ValueError, match="dimension does not match"):
        await context.create_retrieval_service("assessment-001")
