from abc import ABC, abstractmethod

from app.schemas.embedding import EmbeddingVector


class BaseEmbeddingProvider(ABC):
    """Contract implemented by embedding providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the embedding provider name."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the configured embedding model name."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the output-vector dimension."""

    @abstractmethod
    def embed_documents(
        self,
        texts: list[str],
    ) -> list:
        """Generate embeddings for document text."""

    @abstractmethod
    def embed_query(
        self,
        text: str,
    ) -> EmbeddingVector:
        """Generate an embedding for a search query."""
