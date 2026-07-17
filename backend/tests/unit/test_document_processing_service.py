import pytest

from app.documents.parsers import (
    PypdfPDFParser,
    Utf8TextDocumentParser,
)
from app.documents.registry import DocumentParserRegistry
from app.repositories.document import InMemoryDocumentRepository
from app.repositories.extracted_document import (
    InMemoryExtractedDocumentRepository,
)
from app.schemas.document import DocumentType
from app.schemas.document_upload import (
    DocumentLifecycleStatus,
    DocumentPurpose,
    DocumentUploadMetadata,
)
from app.services.document_extraction_service import DocumentExtractionService
from app.services.document_processing_service import DocumentProcessingService
from app.services.document_service import DocumentService
from app.services.document_validation_service import DocumentValidationService
from app.storage.document_storage import InMemoryDocumentStorage


def create_services() -> tuple[DocumentService, DocumentProcessingService]:
    """Create document services sharing repositories and storage."""

    document_repository = InMemoryDocumentRepository()
    extracted_repository = InMemoryExtractedDocumentRepository()
    storage = InMemoryDocumentStorage()
    registry = DocumentParserRegistry()
    registry.register(PypdfPDFParser())
    registry.register(Utf8TextDocumentParser())

    upload_service = DocumentService(
        repository=document_repository,
        storage=storage,
        validation_service=DocumentValidationService(),
    )
    processing_service = DocumentProcessingService(
        document_repository=document_repository,
        extracted_document_repository=extracted_repository,
        storage=storage,
        extraction_service=DocumentExtractionService(registry=registry),
    )
    return upload_service, processing_service


@pytest.mark.asyncio
async def test_processing_extracts_stored_text_document() -> None:
    upload_service, processing_service = create_services()

    upload = await upload_service.upload_document(
        original_file_name="proposal.txt",
        declared_media_type="text/plain",
        content=b"Synthetic proposal content.",
        metadata=DocumentUploadMetadata(
            purpose=DocumentPurpose.PROPOSAL,
        ),
    )

    await processing_service.request_extraction(
        upload.document_id,
    )

    extracted = await processing_service.extract_document(
        upload.document_id,
    )

    status = await upload_service.get_status(
        upload.document_id,
    )

    assert extracted.document_id == upload.document_id
    assert extracted.file_name == "proposal.txt"
    assert extracted.document_type is DocumentType.TEXT
    assert extracted.page_count == 1

    assert status.lifecycle_status is DocumentLifecycleStatus.EXTRACTED
    assert status.page_count == 1
    assert status.extracted_character_count == 27


@pytest.mark.asyncio
async def test_processing_persists_extracted_document() -> None:
    upload_service, processing_service = create_services()

    upload = await upload_service.upload_document(
        original_file_name="proposal.txt",
        declared_media_type="text/plain",
        content=b"Synthetic proposal content.",
        metadata=DocumentUploadMetadata(
            purpose=DocumentPurpose.PROPOSAL,
        ),
    )

    await processing_service.request_extraction(
        upload.document_id,
    )

    extracted = await processing_service.extract_document(
        upload.document_id,
    )

    stored = await processing_service.get_extracted_document(
        upload.document_id,
    )

    assert stored == extracted
    assert stored is not extracted


@pytest.mark.asyncio
async def test_processing_rejects_duplicate_request() -> None:
    upload_service, processing_service = create_services()

    upload = await upload_service.upload_document(
        original_file_name="proposal.txt",
        declared_media_type="text/plain",
        content=b"Synthetic proposal content.",
        metadata=DocumentUploadMetadata(
            purpose=DocumentPurpose.PROPOSAL,
        ),
    )

    first_response = await processing_service.request_extraction(
        upload.document_id,
    )

    assert first_response.lifecycle_status is DocumentLifecycleStatus.EXTRACTION_PENDING

    from app.core.exceptions import DocumentConflictError

    with pytest.raises(
        DocumentConflictError,
        match="only be requested",
    ):
        await processing_service.request_extraction(
            upload.document_id,
        )


@pytest.mark.asyncio
async def test_processing_requires_pending_state() -> None:
    upload_service, processing_service = create_services()

    upload = await upload_service.upload_document(
        original_file_name="proposal.txt",
        declared_media_type="text/plain",
        content=b"Synthetic proposal content.",
        metadata=DocumentUploadMetadata(
            purpose=DocumentPurpose.PROPOSAL,
        ),
    )

    from app.core.exceptions import DocumentConflictError

    with pytest.raises(
        DocumentConflictError,
        match="extraction_pending",
    ):
        await processing_service.extract_document(
            upload.document_id,
        )
