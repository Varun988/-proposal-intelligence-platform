from app.rag.base import BaseDocumentChunker
from app.schemas.chunk import ChunkingResult
from app.schemas.document import ExtractedDocument


class DocumentChunkingService:
    """Coordinate document chunking through a configured strategy."""

    def __init__(
        self,
        chunker: BaseDocumentChunker,
    ) -> None:
        self._chunker = chunker

    def chunk_document(
        self,
        document: ExtractedDocument,
    ) -> ChunkingResult:
        """Convert an extracted document into retrieval-ready chunks."""

        return self._chunker.chunk(document)
