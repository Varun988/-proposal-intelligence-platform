from app.schemas.document_upload import (
    DocumentProcessResponse,
)
from app.services.document_chunk_processing_service import (
    DocumentChunkProcessingService,
)
from app.services.document_indexing_service import (
    DocumentIndexingService,
)
from app.services.document_processing_service import (
    DocumentProcessingService,
)


class DocumentPipelineService:
    """Coordinate extraction, chunking, and indexing."""

    def __init__(
        self,
        extraction_service: DocumentProcessingService,
        chunk_processing_service: DocumentChunkProcessingService,
        indexing_service: DocumentIndexingService,
    ) -> None:
        self._extraction_service = extraction_service
        self._chunk_processing_service = chunk_processing_service
        self._indexing_service = indexing_service

    async def request_processing(
        self,
        document_id: str,
    ) -> DocumentProcessResponse:
        """Atomically queue a stored document for processing."""

        return await self._extraction_service.request_extraction(
            document_id,
        )

    async def process_document(
        self,
        document_id: str,
    ) -> None:
        """Extract, chunk, embed, and index one queued document."""

        await self._extraction_service.extract_document(
            document_id,
        )

        await self._chunk_processing_service.request_chunking(
            document_id,
        )

        await self._chunk_processing_service.chunk_document(
            document_id,
        )

        await self._indexing_service.request_indexing(
            document_id,
        )

        await self._indexing_service.index_document(
            document_id,
        )
