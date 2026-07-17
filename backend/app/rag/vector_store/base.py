from abc import ABC, abstractmethod
from pathlib import Path

from app.schemas.embedding import EmbeddedChunk, EmbeddingVector
from app.schemas.retrieval import VectorSearchResponse


class BaseVectorStore(ABC):
    """Contract implemented by vector-store technologies."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimension supported by the store."""

    @property
    @abstractmethod
    def size(self) -> int:
        """Return the number of indexed vectors."""

    @abstractmethod
    def add(
        self,
        items: list[EmbeddedChunk],
    ) -> None:
        """Add embedded chunks to the vector store."""

    @abstractmethod
    def search(
        self,
        query: EmbeddingVector,
        limit: int = 5,
    ) -> VectorSearchResponse:
        """Return chunks most similar to the query vector."""

    @abstractmethod
    def save(
        self,
        directory: Path,
    ) -> None:
        """Persist the vector index and metadata."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all indexed vectors and metadata."""
