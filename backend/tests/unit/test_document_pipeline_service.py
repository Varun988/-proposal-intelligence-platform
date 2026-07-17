import pytest
from app.services.document_pipeline_service import (
    DocumentPipelineService,
)

from app.documents.parsers import (
    PypdfPDFParser,
    Utf8TextDocumentParser,
)
from app.documents.registry import DocumentParserRegistry
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
from app.schemas.document_upload import (
    DocumentLifecycleStatus,
    DocumentPurpose,
    DocumentUploadMetadata,
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
from app.services.document_processing_service import (
    DocumentProcessingService,
)
from app.services.document_service import DocumentService
from app.services.document_validation_service import (
    DocumentValidationService,
)
from app.storage.document_storage import (
    InMemoryDocumentStorage,
)


def create_services() -> tuple[
    DocumentService,
    DocumentPipelineService,
    InMemoryDocumentChunkRepository,
]:
    """Create document services sharing the same dependencies."""

    document_repository = InMemoryDocumentRepository()

    extracted_repository = InMemoryExtractedDocumentRepository()

    chunk_repository = InMemoryDocumentChunkRepository()

    storage = InMemoryDocumentStorage()

    registry = DocumentParserRegistry()

    registry.register(
        PypdfPDFParser(),
    )
    registry.register(
        Utf8TextDocumentParser(),
    )

    extraction_service = DocumentProcessingService(
        document_repository=document_repository,
        extracted_document_repository=(extracted_repository),
        storage=storage,
        extraction_service=DocumentExtractionService(
            registry=registry,
        ),
    )

    chunk_processing_service = DocumentChunkProcessingService(
        document_repository=document_repository,
        extracted_document_repository=(extracted_repository),
        chunk_repository=chunk_repository,
        chunking_service=DocumentChunkingService(
            chunker=PageAwareDocumentChunker(
                max_characters=500,
                overlap_characters=50,
            ),
        ),
    )

    pipeline_service = DocumentPipelineService(
        extraction_service=extraction_service,
        chunk_processing_service=(chunk_processing_service),
    )

    upload_service = DocumentService(
        repository=document_repository,
        storage=storage,
        validation_service=DocumentValidationService(),
    )

    return (
        upload_service,
        pipeline_service,
        chunk_repository,
    )


@pytest.mark.asyncio
async def test_pipeline_processes_document_to_chunked() -> None:
    (
        upload_service,
        pipeline_service,
        chunk_repository,
    ) = create_services()

    upload = await upload_service.upload_document(
        original_file_name="proposal.txt",
        declared_media_type="text/plain",
        content=b"Synthetic proposal content.",
        metadata=DocumentUploadMetadata(
            purpose=DocumentPurpose.PROPOSAL,
            assessment_id="assessment-001",
        ),
    )

    response = await pipeline_service.request_processing(
        upload.document_id,
    )

    assert response.lifecycle_status is DocumentLifecycleStatus.EXTRACTION_PENDING
    assert response.processing_accepted is True

    await pipeline_service.process_document(
        upload.document_id,
    )

    status = await upload_service.get_status(
        upload.document_id,
    )

    chunks = await chunk_repository.get_chunks(
        upload.document_id,
    )

    assert status.lifecycle_status is DocumentLifecycleStatus.CHUNKED
    assert status.page_count == 1
    assert status.extracted_character_count == 27
    assert status.chunk_count == 1

    assert len(chunks) == 1
    assert chunks[0].document_id == upload.document_id
    assert chunks[0].citation.document_id == upload.document_id


@pytest.mark.asyncio
async def test_pipeline_preserves_chunk_metadata() -> None:
    (
        upload_service,
        pipeline_service,
        chunk_repository,
    ) = create_services()

    upload = await upload_service.upload_document(
        original_file_name="vendor.txt",
        declared_media_type="text/plain",
        content=b"Synthetic vendor profile.",
        metadata=DocumentUploadMetadata(
            purpose=DocumentPurpose.VENDOR_PROFILE,
            vendor_name="Example Digital Services",
            assessment_id="assessment-001",
            source_name="Synthetic Vendor Profile",
            is_public_source=False,
        ),
    )

    await pipeline_service.request_processing(
        upload.document_id,
    )

    await pipeline_service.process_document(
        upload.document_id,
    )

    chunks = await chunk_repository.get_chunks(
        upload.document_id,
    )

    metadata = chunks[0].metadata

    assert metadata["document_purpose"] == ("vendor_profile")
    assert metadata["assessment_id"] == ("assessment-001")
    assert metadata["vendor_name"] == ("Example Digital Services")
    assert metadata["source_name"] == ("Synthetic Vendor Profile")
    assert metadata["is_public_source"] is False


@pytest.mark.asyncio
async def test_pipeline_rejects_duplicate_request() -> None:
    upload_service, pipeline_service, _ = create_services()

    upload = await upload_service.upload_document(
        original_file_name="proposal.txt",
        declared_media_type="text/plain",
        content=b"Synthetic proposal content.",
        metadata=DocumentUploadMetadata(
            purpose=DocumentPurpose.PROPOSAL,
        ),
    )

    await pipeline_service.request_processing(
        upload.document_id,
    )

    from app.core.exceptions import DocumentConflictError

    with pytest.raises(
        DocumentConflictError,
        match="only be requested",
    ):
        await pipeline_service.request_processing(
            upload.document_id,
        )
