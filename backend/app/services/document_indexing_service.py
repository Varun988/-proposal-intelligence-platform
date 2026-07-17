import asyncio

from app.core.exceptions import (
    DocumentConflictError,
    DocumentStorageError,
)
from app.repositories.assessment_vector_index import (
    AssessmentVectorIndexRegistryProtocol,
)
from app.repositories.document import DocumentRepositoryProtocol
from app.repositories.document_chunk import (
    DocumentChunkRepositoryProtocol,
)
from app.schemas.assessment import utc_now
from app.schemas.document_upload import DocumentLifecycleStatus
from app.schemas.vector_index import DocumentIndexingResult
from app.services.embedding_service import EmbeddingService


class DocumentIndexingService:
    """Embed and purpose-index citation-ready document chunks."""

    def __init__(
        self,
        document_repository: DocumentRepositoryProtocol,
        chunk_repository: DocumentChunkRepositoryProtocol,
        index_registry: AssessmentVectorIndexRegistryProtocol,
        embedding_service: EmbeddingService,
    ) -> None:
        self._document_repository = document_repository
        self._chunk_repository = chunk_repository
        self._index_registry = index_registry
        self._embedding_service = embedding_service

    async def request_indexing(self, document_id: str) -> None:
        """Atomically queue a chunked document for indexing."""

        await self._document_repository.claim_indexing(
            document_id=document_id,
            updated_at=utc_now(),
        )

    async def index_document(
        self,
        document_id: str,
    ) -> DocumentIndexingResult:
        """Embed and add a document to its assessment-purpose index."""

        record = await self._document_repository.get(document_id)
        if (
            record.lifecycle_status
            is not DocumentLifecycleStatus.INDEXING_PENDING
        ):
            raise DocumentConflictError(
                "Document indexing requires lifecycle status "
                "'indexing_pending'."
            )
        if not record.assessment_id:
            raise DocumentConflictError(
                "Document indexing requires an assessment ID."
            )

        running_record = record.model_copy(
            update={
                "lifecycle_status": (
                    DocumentLifecycleStatus.INDEXING_RUNNING
                ),
                "error_message": None,
                "updated_at": utc_now(),
            },
            deep=True,
        )
        await self._document_repository.update(running_record)

        try:
            chunks = await self._chunk_repository.get_chunks(document_id)
            if not chunks:
                raise DocumentStorageError(
                    "Document contains no chunks to index."
                )

            embedding_result = await asyncio.to_thread(
                self._embedding_service.embed_chunks,
                chunks,
            )
            metadata = await self._index_registry.add_document(
                assessment_id=record.assessment_id,
                document_id=document_id,
                items=embedding_result.items,
                embedding_provider=embedding_result.provider_name,
                embedding_model=embedding_result.model_name,
                vector_dimension=embedding_result.dimension,
                document_purpose=record.purpose,
            )

            completed_record = running_record.model_copy(
                update={
                    "lifecycle_status": DocumentLifecycleStatus.INDEXED,
                    "error_message": None,
                    "updated_at": utc_now(),
                },
                deep=True,
            )
            await self._document_repository.update(completed_record)

            return DocumentIndexingResult(
                assessment_id=record.assessment_id,
                document_id=document_id,
                indexed_chunk_count=embedding_result.item_count,
                vector_store_size=metadata.vector_store_size,
                vector_dimension=metadata.vector_dimension,
                embedding_provider=embedding_result.provider_name,
                embedding_model=embedding_result.model_name,
            )
        except Exception as error:
            await self._mark_failed(record=running_record, error=error)
            raise

    async def _mark_failed(self, record: object, error: Exception) -> None:
        """Persist a safe indexing failure state."""

        safe_message = (
            "Document indexing failed: "
            f"{type(error).__name__}."
        )
        failed_record = record.model_copy(
            update={
                "lifecycle_status": DocumentLifecycleStatus.FAILED,
                "error_message": safe_message,
                "updated_at": utc_now(),
            },
            deep=True,
        )
        await self._document_repository.update(failed_record)
