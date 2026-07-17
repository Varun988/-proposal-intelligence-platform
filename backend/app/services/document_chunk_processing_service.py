from app.core.exceptions import (
    DocumentChunkingError,
    DocumentConflictError,
)
from app.repositories.document import (
    DocumentRepositoryProtocol,
)
from app.repositories.document_chunk import (
    DocumentChunkRepositoryProtocol,
)
from app.repositories.extracted_document import (
    ExtractedDocumentRepositoryProtocol,
)
from app.schemas.assessment import utc_now
from app.schemas.chunk import (
    ChunkingResult,
    DocumentChunk,
)
from app.schemas.document_upload import (
    DocumentLifecycleStatus,
)
from app.services.document_chunking_service import (
    DocumentChunkingService,
)


class DocumentChunkProcessingService:
    """Chunk extracted documents and persist citation-ready output."""

    def __init__(
        self,
        document_repository: DocumentRepositoryProtocol,
        extracted_document_repository: (ExtractedDocumentRepositoryProtocol),
        chunk_repository: DocumentChunkRepositoryProtocol,
        chunking_service: DocumentChunkingService,
    ) -> None:
        self._document_repository = document_repository
        self._extracted_document_repository = extracted_document_repository
        self._chunk_repository = chunk_repository
        self._chunking_service = chunking_service

    async def request_chunking(
        self,
        document_id: str,
    ) -> None:
        """Atomically queue an extracted document for chunking."""

        await self._document_repository.claim_chunking(
            document_id=document_id,
            updated_at=utc_now(),
        )

    async def chunk_document(
        self,
        document_id: str,
    ) -> ChunkingResult:
        """Create and persist citation-ready document chunks."""

        record = await self._document_repository.get(
            document_id,
        )

        if record.lifecycle_status is not DocumentLifecycleStatus.CHUNKING_PENDING:
            raise DocumentConflictError(
                "Document chunking requires lifecycle status 'chunking_pending'."
            )

        running_record = record.model_copy(
            update={
                "lifecycle_status": (DocumentLifecycleStatus.CHUNKING_RUNNING),
                "error_message": None,
                "updated_at": utc_now(),
            },
            deep=True,
        )

        await self._document_repository.update(
            running_record,
        )

        try:
            extracted_document = await self._extracted_document_repository.get(document_id)

            result = self._chunking_service.chunk_document(
                extracted_document,
            )

            enriched_result = self._enrich_result(
                result=result,
                document_record=running_record,
            )

            if not enriched_result.chunks:
                raise DocumentChunkingError("Document chunking produced no text chunks.")

            await self._chunk_repository.create(
                enriched_result,
            )

            completed_record = running_record.model_copy(
                update={
                    "lifecycle_status": (DocumentLifecycleStatus.CHUNKED),
                    "chunk_count": (enriched_result.chunk_count),
                    "error_message": None,
                    "updated_at": utc_now(),
                },
                deep=True,
            )

            await self._document_repository.update(
                completed_record,
            )

            return enriched_result.model_copy(
                deep=True,
            )

        except Exception as error:
            await self._mark_failed(
                record=running_record,
                error=error,
            )

            if isinstance(error, DocumentChunkingError):
                raise

            raise DocumentChunkingError("Stored document chunking failed.") from error

    async def get_chunks(
        self,
        document_id: str,
    ) -> list:
        """Retrieve citation-ready chunks for one document."""

        return await self._chunk_repository.get_chunks(
            document_id,
        )

    @staticmethod
    def _enrich_result(
        result: ChunkingResult,
        document_record: object,
    ) -> ChunkingResult:
        """Add trusted upload metadata to generated chunks."""

        enriched_chunks: list[DocumentChunk] = []

        for chunk in result.chunks:
            metadata = dict(chunk.metadata)

            metadata.update(
                {
                    "document_purpose": (document_record.purpose.value),
                    "original_file_name": (document_record.original_file_name),
                    "media_type": (document_record.media_type.value),
                    "assessment_id": (document_record.assessment_id),
                    "vendor_name": (document_record.vendor_name),
                    "source_name": (document_record.source_name),
                    "is_public_source": (document_record.is_public_source),
                }
            )

            enriched_chunk = chunk.model_copy(
                update={
                    "metadata": metadata,
                },
                deep=True,
            )

            enriched_chunks.append(
                enriched_chunk,
            )

        return result.model_copy(
            update={
                "chunks": enriched_chunks,
            },
            deep=True,
        )

    async def _mark_failed(
        self,
        record: object,
        error: Exception,
    ) -> None:
        """Persist a safe chunking failure state."""

        safe_message = f"Document chunking failed: {type(error).__name__}."

        failed_record = record.model_copy(
            update={
                "lifecycle_status": (DocumentLifecycleStatus.FAILED),
                "error_message": safe_message,
                "updated_at": utc_now(),
            },
            deep=True,
        )

        await self._document_repository.update(
            failed_record,
        )
