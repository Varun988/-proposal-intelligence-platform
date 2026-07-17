from typing import Any

from app.core.exceptions import (
    EmbeddingConfigurationError,
    EmbeddingDimensionError,
    EmbeddingProviderError,
)
from app.rag.embeddings.base import BaseEmbeddingProvider
from app.schemas.embedding import EmbeddingVector


class SentenceTransformerEmbeddingProvider(
    BaseEmbeddingProvider,
):
    """Generate local embeddings using a Sentence Transformer model."""

    def __init__(
        self,
        model_name: str,
        model: Any | None = None,
        normalize_embeddings: bool = True,
    ) -> None:
        normalized_model_name = model_name.strip()

        if not normalized_model_name:
            raise EmbeddingConfigurationError("Embedding model name is required.")

        self._model_name = normalized_model_name
        self._normalize_embeddings = normalize_embeddings

        self._model = model or self._load_model(
            normalized_model_name,
        )

        self._dimension = self._get_model_dimension()

    @property
    def provider_name(self) -> str:
        """Return the embedding-provider name."""

        return "sentence-transformers"

    @property
    def model_name(self) -> str:
        """Return the configured embedding-model name."""

        return self._model_name

    @property
    def dimension(self) -> int:
        """Return the model output-vector dimension."""

        return self._dimension

    def embed_documents(
        self,
        texts: list[str],
    ) -> list:
        """Generate embeddings for document passages."""

        if not texts:
            return []

        normalized_texts = [self._validate_text(text) for text in texts]

        vectors = self._encode(
            normalized_texts,
        )

        return [self._to_embedding_vector(vector) for vector in vectors]

    def embed_query(
        self,
        text: str,
    ) -> EmbeddingVector:
        """Generate an embedding for a search query."""

        normalized_text = self._validate_text(
            text,
        )

        vectors = self._encode(
            [normalized_text],
        )

        if len(vectors) != 1:
            raise EmbeddingProviderError(
                "Embedding model returned an unexpected number of query vectors."
            )

        return self._to_embedding_vector(
            vectors[0],
        )

    @staticmethod
    def _load_model(
        model_name: str,
    ) -> Any:
        """Load a Sentence Transformer model on the CPU."""

        try:
            from sentence_transformers import (
                SentenceTransformer,
            )

            return SentenceTransformer(
                model_name,
                device="cpu",
            )
        except Exception as error:
            raise EmbeddingProviderError(
                "Unable to load the Sentence Transformer model."
            ) from error

    def _get_model_dimension(self) -> int:
        """Read and validate the model embedding dimension."""

        try:
            if hasattr(
                self._model,
                "get_embedding_dimension",
            ):
                dimension = self._model.get_embedding_dimension()
            else:
                dimension = self._model.get_sentence_embedding_dimension()
        except Exception as error:
            raise EmbeddingProviderError("Unable to determine the embedding dimension.") from error

        if not isinstance(dimension, int) or dimension < 1:
            raise EmbeddingDimensionError("Embedding model returned an invalid dimension.")

        return dimension

    def _encode(
        self,
        texts: list[str],
    ) -> list:
        """Encode text using the configured local model."""

        try:
            vectors = self._model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=(self._normalize_embeddings),
                show_progress_bar=False,
            )
        except Exception as error:
            raise EmbeddingProviderError("Sentence Transformer encoding failed.") from error

        try:
            return list(vectors)
        except TypeError as error:
            raise EmbeddingProviderError(
                "Embedding model returned an invalid vector collection."
            ) from error

    def _to_embedding_vector(
        self,
        vector: Any,
    ) -> EmbeddingVector:
        """Convert a model vector into the shared schema."""

        try:
            if hasattr(vector, "tolist"):
                raw_values = vector.tolist()
            else:
                raw_values = list(vector)

            values = [float(value) for value in raw_values]
        except (
            AttributeError,
            TypeError,
            ValueError,
        ) as error:
            raise EmbeddingProviderError("Embedding model returned an invalid vector.") from error

        embedding = EmbeddingVector(
            values=values,
        )

        if embedding.dimension != self.dimension:
            raise EmbeddingDimensionError(
                "Generated embedding dimension does not match "
                f"the model dimension. Generated: "
                f"{embedding.dimension}. Expected: "
                f"{self.dimension}."
            )

        return embedding

    @staticmethod
    def _validate_text(
        text: str,
    ) -> str:
        """Validate and normalize text before embedding."""

        normalized_text = text.strip()

        if not normalized_text:
            raise ValueError("Text to embed cannot be empty.")

        return normalized_text
