from app.rag.embeddings.base import BaseEmbeddingProvider
from app.schemas.embedding import EmbeddingVector


class FakeEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic embedding provider used by unit tests."""

    def __init__(
        self,
        dimension: int = 3,
    ) -> None:
        self._dimension = dimension
        self.received_document_texts: list[str] = []
        self.received_queries: list[str] = []

    @property
    def provider_name(self) -> str:
        """Return the fake provider name."""

        return "fake-embeddings"

    @property
    def model_name(self) -> str:
        """Return the fake embedding model name."""

        return "fake-embedding-model"

    @property
    def dimension(self) -> int:
        """Return the configured embedding dimension."""

        return self._dimension

    def embed_documents(
        self,
        texts: list[str],
    ) -> list:
        """Create deterministic vectors for document text."""

        self.received_document_texts.extend(texts)

        return [self._create_vector(text) for text in texts]

    def embed_query(
        self,
        text: str,
    ) -> EmbeddingVector:
        """Create a deterministic vector for a search query."""

        self.received_queries.append(text)

        return self._create_vector(text)

    def _create_vector(
        self,
        text: str,
    ) -> EmbeddingVector:
        """Create a deterministic embedding from text properties."""

        base_values = [
            float(len(text)),
            float(len(text.split())),
            float(sum(ord(character) for character in text) % 100),
        ]

        if self._dimension <= len(base_values):
            values = base_values[: self._dimension]
        else:
            values = base_values + [0.0 for _ in range(self._dimension - len(base_values))]

        return EmbeddingVector(values=values)


class InvalidDimensionEmbeddingProvider(
    FakeEmbeddingProvider,
):
    """Fake provider that deliberately returns incorrect dimensions."""

    def embed_documents(
        self,
        texts: list[str],
    ) -> list:
        """Return invalid two-dimensional document vectors."""

        self.received_document_texts.extend(texts)

        return [
            EmbeddingVector(
                values=[1.0, 2.0],
            )
            for _ in texts
        ]

    def embed_query(
        self,
        text: str,
    ) -> EmbeddingVector:
        """Return an invalid two-dimensional query vector."""

        self.received_queries.append(text)

        return EmbeddingVector(
            values=[1.0, 2.0],
        )
