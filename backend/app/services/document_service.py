from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from app.repositories.document import DocumentRepositoryProtocol
from app.schemas.assessment import utc_now
from app.schemas.document_upload import (
    DocumentLifecycleStatus,
    DocumentStatusResponse,
    DocumentUploadMetadata,
    DocumentUploadResponse,
    StoredDocumentRecord,
)
from app.services.document_validation_service import (
    DocumentValidationService,
)
from app.storage.document_storage import DocumentStorageProtocol


class DocumentService:
    """Validate, store, and retrieve document metadata."""

    def __init__(
        self,
        repository: DocumentRepositoryProtocol,
        storage: DocumentStorageProtocol,
        validation_service: DocumentValidationService,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._validation_service = validation_service

    async def upload_document(
        self,
        original_file_name: str,
        declared_media_type: str | None,
        content: bytes,
        metadata: DocumentUploadMetadata,
    ) -> DocumentUploadResponse:
        """Validate and persist an uploaded document."""

        media_type = self._validation_service.validate(
            original_file_name=original_file_name,
            declared_media_type=declared_media_type,
            content=content,
        )

        document_id = f"document-{uuid4()}"
        extension = Path(original_file_name).suffix.casefold()
        storage_file_name = f"{document_id}{extension}"

        timestamp = utc_now()
        checksum = sha256(content).hexdigest()

        await self._storage.save(
            storage_file_name=storage_file_name,
            content=content,
        )

        record = StoredDocumentRecord(
            document_id=document_id,
            original_file_name=Path(
                original_file_name
            ).name,
            storage_file_name=storage_file_name,
            media_type=media_type,
            purpose=metadata.purpose,
            lifecycle_status=DocumentLifecycleStatus.STORED,
            file_size_bytes=len(content),
            checksum_sha256=checksum,
            vendor_name=metadata.vendor_name,
            assessment_id=metadata.assessment_id,
            source_name=metadata.source_name,
            is_public_source=metadata.is_public_source,
            created_at=timestamp,
            updated_at=timestamp,
        )

        try:
            stored_record = await self._repository.create(record)
        except Exception:
            await self._storage.delete(storage_file_name)
            raise

        return self._to_upload_response(stored_record)

    async def get_document(
        self,
        document_id: str,
    ) -> StoredDocumentRecord:
        """Return internal document metadata."""

        return await self._repository.get(document_id)

    async def get_status(
        self,
        document_id: str,
    ) -> DocumentStatusResponse:
        """Return public document-processing status."""

        record = await self._repository.get(document_id)

        return DocumentStatusResponse(
            document_id=record.document_id,
            original_file_name=record.original_file_name,
            purpose=record.purpose,
            lifecycle_status=record.lifecycle_status,
            page_count=record.page_count,
            chunk_count=record.chunk_count,
            error_message=record.error_message,
            created_at=record.created_at,
            updated_at=record.updated_at,
            extracted_character_count=(
            record.extracted_character_count
        ),
        )

    async def read_content(
        self,
        document_id: str,
    ) -> bytes:
        """Read stored content using a document ID."""

        record = await self._repository.get(document_id)

        return await self._storage.read(
            record.storage_file_name
        )

    @staticmethod
    def _to_upload_response(
        record: StoredDocumentRecord,
    ) -> DocumentUploadResponse:
        """Convert an internal record to an upload response."""

        return DocumentUploadResponse(
            document_id=record.document_id,
            original_file_name=record.original_file_name,
            media_type=record.media_type,
            purpose=record.purpose,
            lifecycle_status=record.lifecycle_status,
            file_size_bytes=record.file_size_bytes,
            checksum_sha256=record.checksum_sha256,
            created_at=record.created_at,
        )
