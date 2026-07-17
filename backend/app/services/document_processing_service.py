import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from app.core.exceptions import (
    DocumentConflictError,
    DocumentExtractionError,
)
from app.repositories.document import DocumentRepositoryProtocol
from app.repositories.extracted_document import (
    ExtractedDocumentRepositoryProtocol,
)
from app.schemas.assessment import utc_now
from app.schemas.document import ExtractedDocument
from app.schemas.document_upload import (
    DocumentLifecycleStatus,
    DocumentProcessResponse,
)
from app.services.document_extraction_service import DocumentExtractionService
from app.storage.document_storage import DocumentStorageProtocol


class DocumentProcessingService:
    """Extract stored documents and persist their lifecycle metadata."""

    def __init__(
        self,
        document_repository: DocumentRepositoryProtocol,
        extracted_document_repository: ExtractedDocumentRepositoryProtocol,
        storage: DocumentStorageProtocol,
        extraction_service: DocumentExtractionService,
    ) -> None:
        self._document_repository = document_repository
        self._extracted_document_repository = extracted_document_repository
        self._storage = storage
        self._extraction_service = extraction_service

    async def request_extraction(
        self,
        document_id: str,
    ) -> DocumentProcessResponse:
        """Atomically queue one document for extraction."""

        record = await self._document_repository.claim_extraction(
            document_id=document_id,
            updated_at=utc_now(),
        )

        return DocumentProcessResponse(
            document_id=record.document_id,
            lifecycle_status=record.lifecycle_status,
            processing_accepted=True,
            message=("Document extraction was accepted and queued."),
        )

    async def extract_document(self, document_id: str) -> ExtractedDocument:
        """Extract one stored PDF or UTF-8 text document."""

        record = await self._document_repository.get(
            document_id,
        )

        if record.lifecycle_status is not DocumentLifecycleStatus.EXTRACTION_PENDING:
            raise DocumentConflictError(
                "Document extraction requires lifecycle status 'extraction_pending'."
            )

        running_record = record.model_copy(
            update={
                "lifecycle_status": DocumentLifecycleStatus.EXTRACTION_RUNNING,
                "error_message": None,
                "updated_at": utc_now(),
            },
            deep=True,
        )
        await self._document_repository.update(running_record)

        try:
            content = await self._storage.read(record.storage_file_name)
            extracted = await self._extract_from_temporary_file(
                storage_file_name=record.storage_file_name,
                content=content,
            )
            canonical = extracted.model_copy(
                update={
                    "document_id": record.document_id,
                    "file_name": record.original_file_name,
                    "file_path": Path(record.storage_file_name),
                    "checksum_sha256": record.checksum_sha256,
                },
                deep=True,
            )
            await self._extracted_document_repository.create(canonical)

            completed_record = running_record.model_copy(
                update={
                    "lifecycle_status": DocumentLifecycleStatus.EXTRACTED,
                    "page_count": canonical.page_count,
                    "extracted_character_count": (canonical.extracted_character_count),
                    "error_message": None,
                    "updated_at": utc_now(),
                },
                deep=True,
            )
            await self._document_repository.update(completed_record)
            return canonical.model_copy(deep=True)
        except Exception as error:
            await self._mark_failed(record=running_record, error=error)
            if isinstance(error, DocumentExtractionError):
                raise
            raise DocumentExtractionError("Stored document extraction failed.") from error

    async def get_extracted_document(
        self,
        document_id: str,
    ) -> ExtractedDocument:
        """Retrieve one extracted document."""

        return await self._extracted_document_repository.get(document_id)

    async def _extract_from_temporary_file(
        self,
        storage_file_name: str,
        content: bytes,
    ) -> ExtractedDocument:
        """Write bytes to an isolated temporary file and extract them."""

        with TemporaryDirectory(prefix="proposal-intelligence-") as directory:
            file_path = Path(directory) / Path(storage_file_name).name
            await asyncio.to_thread(file_path.write_bytes, content)
            return await asyncio.to_thread(
                self._extraction_service.extract,
                file_path,
            )

    async def _mark_failed(self, record: object, error: Exception) -> None:
        """Persist a safe extraction failure state."""

        safe_message = f"Document extraction failed: {type(error).__name__}."
        failed_record = record.model_copy(
            update={
                "lifecycle_status": DocumentLifecycleStatus.FAILED,
                "error_message": safe_message,
                "updated_at": utc_now(),
            },
            deep=True,
        )
        await self._document_repository.update(failed_record)
