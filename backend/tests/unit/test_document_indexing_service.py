import pytest

from app.core.exceptions import DocumentConflictError
from app.rag.vector_store.faiss_store import FaissVectorStore
from app.repositories.assessment_vector_index import (
    InMemoryAssessmentVectorIndexRegistry,
)
from app.repositories.document import (
    InMemoryDocumentRepository,
)
from app.repositories.document_chunk import (
    InMemoryDocumentChunkRepository,
)
from app.schemas.assessment import utc_now
from app.schemas.chunk import (
    ChunkCitation,
    ChunkingResult,
    DocumentChunk,
)
from app.schemas.document_upload import (
    DocumentLifecycleStatus,
    DocumentMediaType,
    DocumentPurpose,
    StoredDocumentRecord,
)
from app.services.document_indexing_service import (
    DocumentIndexingService,
)
from app.services.embedding_service import EmbeddingService
from tests.embedding_fakes import FakeEmbeddingProvider


async def create_service(
    assessment_id: str | None = "assessment-001",
) -> tuple[
    DocumentIndexingService,
    InMemoryDocumentRepository,
    InMemoryAssessmentVectorIndexRegistry,
    FakeEmbeddingProvider,
]:
    """Create an indexing service with one chunked document."""

    document_repository = InMemoryDocumentRepository()
    chunk_repository = InMemoryDocumentChunkRepository()

    index_registry = InMemoryAssessmentVectorIndexRegistry(
        vector_store_factory=lambda dimension: FaissVectorStore(
            dimension=dimension,
        )
    )

    embedding_provider = FakeEmbeddingProvider(
        dimension=3,
    )

    embedding_service = EmbeddingService(
        provider=embedding_provider,
    )

    timestamp = utc_now()

    record = StoredDocumentRecord(
        document_id="document-001",
        original_file_name="proposal.txt",
        storage_file_name="document-001.txt",
        media_type=DocumentMediaType.TEXT,
        purpose=DocumentPurpose.PROPOSAL,
        lifecycle_status=DocumentLifecycleStatus.CHUNKED,
        file_size_bytes=27,
        checksum_sha256="a" * 64,
        assessment_id=assessment_id,
        page_count=1,
        extracted_character_count=27,
        chunk_count=1,
        created_at=timestamp,
        updated_at=timestamp,
    )

    chunk = DocumentChunk(
        chunk_id="chunk-001",
        document_id="document-001",
        text="Synthetic proposal content.",
        page_number=1,
        page_chunk_index=0,
        document_chunk_index=0,
        citation=ChunkCitation(
            document_id="document-001",
            file_name="proposal.txt",
            page_number=1,
            checksum_sha256="a" * 64,
        ),
        metadata={
            "document_purpose": "proposal",
            "assessment_id": assessment_id,
        },
    )

    chunking_result = ChunkingResult(
        document_id="document-001",
        chunks=[chunk],
        source_character_count=27,
        chunk_character_count=27,
    )

    await document_repository.create(record)
    await chunk_repository.create(chunking_result)

    service = DocumentIndexingService(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        index_registry=index_registry,
        embedding_service=embedding_service,
    )

    return (
        service,
        document_repository,
        index_registry,
        embedding_provider,
    )


@pytest.mark.asyncio
async def test_service_indexes_chunked_document() -> None:
    (
        service,
        document_repository,
        index_registry,
        embedding_provider,
    ) = await create_service()

    await service.request_indexing(
        "document-001",
    )

    result = await service.index_document(
        "document-001",
    )

    record = await document_repository.get(
        "document-001",
    )

    metadata = await index_registry.get_metadata(
        "assessment-001",
    )

    assert result.assessment_id == "assessment-001"
    assert result.document_id == "document-001"
    assert result.indexed_chunk_count == 1
    assert result.vector_store_size == 1
    assert result.vector_dimension == 3
    assert result.embedding_provider == "fake-embeddings"
    assert result.embedding_model == "fake-embedding-model"

    assert record.lifecycle_status is DocumentLifecycleStatus.INDEXED

    assert metadata.document_ids == [
        "document-001",
    ]

    assert embedding_provider.received_document_texts == [
        "Synthetic proposal content.",
    ]


@pytest.mark.asyncio
async def test_service_registers_document_in_assessment_index() -> None:
    (
        service,
        _,
        index_registry,
        _,
    ) = await create_service()

    await service.request_indexing(
        "document-001",
    )

    await service.index_document(
        "document-001",
    )

    assert (
        await index_registry.contains_document(
            "assessment-001",
            "document-001",
        )
        is True
    )

    assert (
        await index_registry.contains_document(
            "assessment-002",
            "document-001",
        )
        is False
    )


@pytest.mark.asyncio
async def test_service_rejects_indexing_without_claim() -> None:
    service, _, _, _ = await create_service()

    with pytest.raises(
        DocumentConflictError,
        match="indexing_pending",
    ):
        await service.index_document(
            "document-001",
        )


@pytest.mark.asyncio
async def test_service_rejects_duplicate_indexing_request() -> None:
    service, _, _, _ = await create_service()

    await service.request_indexing(
        "document-001",
    )

    with pytest.raises(
        DocumentConflictError,
        match="only be requested",
    ):
        await service.request_indexing(
            "document-001",
        )


@pytest.mark.asyncio
async def test_service_rejects_document_without_assessment() -> None:
    service, _, _, _ = await create_service(
        assessment_id=None,
    )

    with pytest.raises(
        DocumentConflictError,
        match="requires an assessment ID",
    ):
        await service.request_indexing(
            "document-001",
        )
