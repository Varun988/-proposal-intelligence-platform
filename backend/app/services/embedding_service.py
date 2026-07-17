from app.core.exceptions import (
    EmbeddingDimensionError,
    EmbeddingProviderError,
)
from app.rag.embeddings.base import BaseEmbeddingProvider
from app.schemas.chunk import DocumentChunk
from app.schemas.embedding import (
    EmbeddedChunk,
    EmbeddingBatchResult,
    EmbeddingVector,
)


class EmbeddingService:
    """Generate and validate embeddings for chunks and queries."""

    def __init__(
        self,
        provider: BaseEmbeddingProvider,
    ) -> None:
        self._provider = provider

    @property
    def provider_name(self) -> str:
        """Return the configured embedding-provider name."""

        return self._provider.provider_name

    @property
    def model_name(self) -> str:
        """Return the configured embedding-model name."""

        return self._provider.model_name

    @property
    def dimension(self) -> int:
        """Return the configured vector dimension."""

        return self._provider.dimension

    def embed_chunks(
        self,
        chunks: list[DocumentChunk],
    ) -> EmbeddingBatchResult:
        """Generate validated embeddings for document chunks."""

        if not chunks:
            return EmbeddingBatchResult(
                items=[],
                provider_name=self.provider_name,
                model_name=self.model_name,
                dimension=self.dimension,
            )

        vectors = self._provider.embed_documents([chunk.text for chunk in chunks])

        if len(vectors) != len(chunks):
            raise EmbeddingProviderError(
                "Embedding provider returned an unexpected number of vectors."
            )

        self._validate_vectors(vectors)

        items = [
            EmbeddedChunk(
                chunk=chunk,
                embedding=vector,
                model_name=self.model_name,
                provider_name=self.provider_name,
            )
            for chunk, vector in zip(
                chunks,
                vectors,
                strict=True,
            )
        ]

        return EmbeddingBatchResult(
            items=items,
            provider_name=self.provider_name,
            model_name=self.model_name,
            dimension=self.dimension,
        )

    def embed_query(
        self,
        query: str,
    ) -> EmbeddingVector:
        """Generate and validate an embedding for a search query."""

        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError("Search query cannot be empty.")

        vector = self._provider.embed_query(
            normalized_query,
        )

        self._validate_vector(vector)

        return vector

    def _validate_vectors(
        self,
        vectors: list[EmbeddingVector],
    ) -> None:
        """Validate all vectors returned by the provider."""

        for vector in vectors:
            self._validate_vector(vector)

    def _validate_vector(
        self,
        vector: EmbeddingVector,
    ) -> None:
        """Validate one vector against the provider dimension."""

        if vector.dimension != self.dimension:
            raise EmbeddingDimensionError(
                "Embedding provider returned an unexpected "
                f"dimension: {vector.dimension}. "
                f"Expected: {self.dimension}."
            )
