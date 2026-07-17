from pathlib import Path

import pytest

from app.core.exceptions import DocumentConflictError
from app.rag.chunking import PageAwareDocumentChunker
from app.repositories.document import (
    InMemoryDocumentRepository,
)
from app.repositories.document_chunk import (
    InMemoryDocumentChunkRepository,
)
from app.repositories.extracted_document import (
    InMemoryExtractedDocumentRepository,
)
from app.schemas.assessment import utc_now
from app.schemas.document import (
    DocumentPage,
    DocumentType,
    ExtractedDocument,
)
from app.schemas.document_upload import (
    DocumentLifecycleStatus,
    DocumentMediaType,
    DocumentPurpose,
    StoredDocumentRecord,
)
from app.services.document_chunk_processing_service import (
    DocumentChunkProcessingService,
)
from app.services.document_chunking_service import (
    DocumentChunkingService,
)


async def create_service() -> tuple[
    DocumentChunkProcessingService,
    InMemoryDocumentRepository,
]:
    """Create a chunk-processing service with test data."""

    document_repository = InMemoryDocumentRepository()
    extracted_repository = InMemoryExtractedDocumentRepository()
    chunk_repository = InMemoryDocumentChunkRepository()

    timestamp = utc_now()

    record = StoredDocumentRecord(
        document_id="document-001",
        original_file_name="proposal.txt",
        storage_file_name="document-001.txt",
        media_type=DocumentMediaType.TEXT,
        purpose=DocumentPurpose.PROPOSAL,
        lifecycle_status=(DocumentLifecycleStatus.EXTRACTED),
        file_size_bytes=27,
        checksum_sha256="a" * 64,
        assessment_id="assessment-001",
        vendor_name="Example Digital Services",
        source_name="Uploaded Proposal",
        is_public_source=False,
        page_count=1,
        extracted_character_count=27,
        created_at=timestamp,
        updated_at=timestamp,
    )

    extracted = ExtractedDocument(
        document_id="document-001",
        file_name="proposal.txt",
        file_path=Path("document-001.txt"),
        document_type=DocumentType.TEXT,
        mime_type="text/plain",
        checksum_sha256="a" * 64,
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                text="Synthetic proposal content.",
            )
        ],
    )

    await document_repository.create(record)
    await extracted_repository.create(extracted)

    service = DocumentChunkProcessingService(
        document_repository=document_repository,
        extracted_document_repository=(extracted_repository),
        chunk_repository=chunk_repository,
        chunking_service=DocumentChunkingService(
            chunker=PageAwareDocumentChunker(
                max_characters=500,
                overlap_characters=50,
            )
        ),
    )

    return service, document_repository


@pytest.mark.asyncio
async def test_service_chunks_extracted_document() -> None:
    service, repository = await create_service()

    await service.request_chunking(
        "document-001",
    )

    result = await service.chunk_document(
        "document-001",
    )

    record = await repository.get(
        "document-001",
    )

    assert result.document_id == "document-001"
    assert result.chunk_count == 1

    assert record.lifecycle_status is DocumentLifecycleStatus.CHUNKED

    assert record.chunk_count == 1


@pytest.mark.asyncio
async def test_service_enriches_chunk_metadata() -> None:
    service, _ = await create_service()

    await service.request_chunking(
        "document-001",
    )

    result = await service.chunk_document(
        "document-001",
    )

    metadata = result.chunks[0].metadata

    assert metadata["document_purpose"] == "proposal"
    assert metadata["assessment_id"] == "assessment-001"
    assert metadata["vendor_name"] == "Example Digital Services"
    assert metadata["source_name"] == "Uploaded Proposal"
    assert metadata["is_public_source"] is False
    assert metadata["media_type"] == "text/plain"


@pytest.mark.asyncio
async def test_service_persists_chunks() -> None:
    service, _ = await create_service()

    await service.request_chunking(
        "document-001",
    )

    result = await service.chunk_document(
        "document-001",
    )

    chunks = await service.get_chunks(
        "document-001",
    )

    assert chunks == result.chunks
    assert chunks is not result.chunks


@pytest.mark.asyncio
async def test_service_rejects_chunking_without_claim() -> None:
    service, _ = await create_service()

    with pytest.raises(
        DocumentConflictError,
        match="chunking_pending",
    ):
        await service.chunk_document(
            "document-001",
        )


@pytest.mark.asyncio
async def test_service_rejects_duplicate_chunking_request() -> None:
    service, _ = await create_service()

    await service.request_chunking(
        "document-001",
    )

    with pytest.raises(
        DocumentConflictError,
        match="only be requested",
    ):
        await service.request_chunking(
            "document-001",
        )
