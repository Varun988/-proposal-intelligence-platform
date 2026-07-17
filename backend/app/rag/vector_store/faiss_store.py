import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from app.core.exceptions import (
    EmptyVectorStoreError,
    VectorDimensionMismatchError,
    VectorStoreConfigurationError,
    VectorStoreError,
)
from app.rag.vector_store.base import BaseVectorStore
from app.schemas.embedding import EmbeddedChunk, EmbeddingVector
from app.schemas.retrieval import (
    VectorSearchResponse,
    VectorSearchResult,
)


class FaissVectorStore(BaseVectorStore):
    """Store and search normalized vectors using FAISS."""

    def __init__(
        self,
        dimension: int,
        normalize_vectors: bool = True,
    ) -> None:
        if dimension < 1:
            raise VectorStoreConfigurationError("Vector-store dimension must be at least 1.")

        self._dimension = dimension
        self._normalize_vectors = normalize_vectors
        self._index = faiss.IndexFlatIP(dimension)
        self._items: list[EmbeddedChunk] = []

    @property
    def dimension(self) -> int:
        """Return the vector dimension supported by the store."""

        return self._dimension

    @property
    def size(self) -> int:
        """Return the number of vectors in the store."""

        return int(self._index.ntotal)

    def add(
        self,
        items: list[EmbeddedChunk],
    ) -> None:
        """Add embedded chunks to the FAISS index."""

        if not items:
            return

        self._validate_item_dimensions(items)

        vectors = np.asarray(
            [item.embedding.values for item in items],
            dtype=np.float32,
        )

        vectors = self._prepare_vectors(vectors)

        try:
            self._index.add(vectors)
        except Exception as error:
            raise VectorStoreError("Unable to add vectors to the FAISS index.") from error

        self._items.extend(items)

    def search(
        self,
        query: EmbeddingVector,
        limit: int = 5,
    ) -> VectorSearchResponse:
        """Return chunks most similar to a query vector."""

        if self.size == 0:
            raise EmptyVectorStoreError("Cannot search an empty vector store.")

        if limit < 1:
            raise VectorStoreConfigurationError("Search limit must be at least 1.")

        if query.dimension != self.dimension:
            raise VectorDimensionMismatchError(
                "Query vector dimension does not match the "
                f"FAISS index. Query: {query.dimension}. "
                f"Index: {self.dimension}."
            )

        query_vector = np.asarray(
            [query.values],
            dtype=np.float32,
        )
        query_vector = self._prepare_vectors(query_vector)

        result_limit = min(limit, self.size)

        try:
            scores, indexes = self._index.search(
                query_vector,
                result_limit,
            )
        except Exception as error:
            raise VectorStoreError("FAISS similarity search failed.") from error

        results: list[VectorSearchResult] = []

        for rank, (score, item_index) in enumerate(
            zip(
                scores[0],
                indexes[0],
                strict=True,
            ),
            start=1,
        ):
            if item_index < 0:
                continue

            results.append(
                VectorSearchResult(
                    chunk=self._items[int(item_index)].chunk,
                    score=float(score),
                    rank=rank,
                )
            )

        return VectorSearchResponse(
            results=results,
            query_dimension=query.dimension,
            total_candidates=self.size,
        )

    def save(
        self,
        directory: Path,
    ) -> None:
        """Persist the FAISS index and chunk metadata."""

        normalized_directory = directory.expanduser().resolve()
        normalized_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        index_path = normalized_directory / "index.faiss"
        metadata_path = normalized_directory / "metadata.json"

        try:
            faiss.write_index(
                self._index,
                str(index_path),
            )

            metadata = {
                "dimension": self.dimension,
                "normalize_vectors": self._normalize_vectors,
                "items": [item.model_dump(mode="json") for item in self._items],
            }

            metadata_path.write_text(
                json.dumps(
                    metadata,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception as error:
            raise VectorStoreError("Unable to save the FAISS vector store.") from error

    def clear(self) -> None:
        """Remove indexed vectors and metadata from memory."""

        self._index.reset()
        self._items.clear()

    def _validate_item_dimensions(
        self,
        items: list[EmbeddedChunk],
    ) -> None:
        """Validate vectors before adding them to the index."""

        for item in items:
            if item.embedding.dimension != self.dimension:
                raise VectorDimensionMismatchError(
                    "Embedding dimension does not match the "
                    f"FAISS index. Embedding: "
                    f"{item.embedding.dimension}. "
                    f"Index: {self.dimension}."
                )

    def _prepare_vectors(
        self,
        vectors: np.ndarray[Any, np.dtype[np.float32]],
    ) -> np.ndarray[Any, np.dtype[np.float32]]:
        """Return contiguous vectors prepared for FAISS."""

        prepared_vectors = np.ascontiguousarray(
            vectors,
            dtype=np.float32,
        )

        if self._normalize_vectors:
            faiss.normalize_L2(prepared_vectors)

        return prepared_vectors
