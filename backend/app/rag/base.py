from abc import ABC, abstractmethod

from app.schemas.chunk import ChunkingResult
from app.schemas.document import ExtractedDocument


class BaseDocumentChunker(ABC):
    """Contract implemented by document chunking strategies."""

    @abstractmethod
    def chunk(
        self,
        document: ExtractedDocument,
    ) -> ChunkingResult:
        """Convert an extracted document into retrieval-ready chunks."""
