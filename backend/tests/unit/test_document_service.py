import pytest

from app.repositories.document import (
    InMemoryDocumentRepository,
)
from app.schemas.document_upload import (
    DocumentLifecycleStatus,
    DocumentPurpose,
    DocumentUploadMetadata,
)
from app.services.document_service import DocumentService
from app.services.document_validation_service import (
    DocumentValidationService,
)
from app.storage.document_storage import (
    InMemoryDocumentStorage,
)


def create_service() -> DocumentService:
    """Create an isolated document service."""

    return DocumentService(
        repository=InMemoryDocumentRepository(),
        storage=InMemoryDocumentStorage(),
        validation_service=DocumentValidationService(),
    )


@pytest.mark.asyncio
async def test_service_uploads_text_document() -> None:
    service = create_service()
    content = b"Synthetic proposal content."

    response = await service.upload_document(
        original_file_name="proposal.txt",
        declared_media_type="text/plain",
        content=content,
        metadata=DocumentUploadMetadata(
            purpose=DocumentPurpose.PROPOSAL,
        ),
    )

    assert response.document_id.startswith("document-")
    assert response.original_file_name == "proposal.txt"
    assert response.lifecycle_status is DocumentLifecycleStatus.STORED
    assert response.file_size_bytes == len(content)
    assert len(response.checksum_sha256) == 64


@pytest.mark.asyncio
async def test_service_reads_uploaded_content() -> None:
    service = create_service()
    content = b"Synthetic proposal content."

    response = await service.upload_document(
        original_file_name="proposal.txt",
        declared_media_type="text/plain",
        content=content,
        metadata=DocumentUploadMetadata(
            purpose=DocumentPurpose.PROPOSAL,
        ),
    )

    stored_content = await service.read_content(response.document_id)

    assert stored_content == content


@pytest.mark.asyncio
async def test_service_returns_document_status() -> None:
    service = create_service()

    response = await service.upload_document(
        original_file_name="profile.pdf",
        declared_media_type="application/pdf",
        content=b"%PDF-1.7 synthetic profile",
        metadata=DocumentUploadMetadata(
            purpose=DocumentPurpose.VENDOR_PROFILE,
            vendor_name="Example Digital Services",
        ),
    )

    status = await service.get_status(response.document_id)

    assert status.document_id == response.document_id
    assert status.purpose is DocumentPurpose.VENDOR_PROFILE
    assert status.lifecycle_status is DocumentLifecycleStatus.STORED
    assert status.chunk_count == 0
