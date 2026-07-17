import asyncio
from collections.abc import Callable
from typing import Protocol

from app.core.exceptions import (
    DocumentConflictError,
    DocumentNotFoundError,
)
from app.rag.vector_store.base import BaseVectorStore
from app.schemas.embedding import EmbeddedChunk
from app.schemas.vector_index import (
    AssessmentVectorIndexMetadata,
)


class AssessmentVectorIndexRegistryProtocol(Protocol):
    """Registry contract for assessment-scoped vector stores."""

    async def add_document(
        self,
        assessment_id: str,
        document_id: str,
        items: list[EmbeddedChunk],
        embedding_provider: str,
        embedding_model: str,
        vector_dimension: int,
    ) -> AssessmentVectorIndexMetadata:
        """Add one document to an assessment-scoped index."""

    async def get_store(
        self,
        assessment_id: str,
    ) -> BaseVectorStore:
        """Return the vector store for one assessment."""

    async def get_metadata(
        self,
        assessment_id: str,
    ) -> AssessmentVectorIndexMetadata:
        """Return metadata for one assessment index."""

    async def contains_document(
        self,
        assessment_id: str,
        document_id: str,
    ) -> bool:
        """Return whether a document is already indexed."""


class InMemoryAssessmentVectorIndexRegistry:
    """Concurrency-safe assessment-isolated vector-index registry."""

    def __init__(
        self,
        vector_store_factory: Callable[
            [int],
            BaseVectorStore,
        ],
    ) -> None:
        self._vector_store_factory = vector_store_factory

        self._stores: dict[
            str,
            BaseVectorStore,
        ] = {}

        self._metadata: dict[
            str,
            AssessmentVectorIndexMetadata,
        ] = {}

        self._lock = asyncio.Lock()

    async def add_document(
        self,
        assessment_id: str,
        document_id: str,
        items: list[EmbeddedChunk],
        embedding_provider: str,
        embedding_model: str,
        vector_dimension: int,
    ) -> AssessmentVectorIndexMetadata:
        """Add one document to an assessment-scoped index."""

        normalized_assessment_id = assessment_id.strip()
        normalized_document_id = document_id.strip()

        if not normalized_assessment_id:
            raise ValueError("Assessment ID is required for indexing.")

        if not normalized_document_id:
            raise ValueError("Document ID is required for indexing.")

        if not items:
            raise ValueError("At least one embedded chunk is required.")

        async with self._lock:
            existing_metadata = self._metadata.get(
                normalized_assessment_id,
            )

            if (
                existing_metadata is not None
                and normalized_document_id in existing_metadata.document_ids
            ):
                raise DocumentConflictError(
                    f"Document is already indexed for assessment: {normalized_document_id}."
                )

            store = self._stores.get(
                normalized_assessment_id,
            )

            if store is None:
                store = self._vector_store_factory(
                    vector_dimension,
                )

                self._stores[normalized_assessment_id] = store

            if store.dimension != vector_dimension:
                raise ValueError(
                    "Assessment index vector dimension does not match the embedding dimension."
                )

            store.add(items)

            document_ids = (
                list(existing_metadata.document_ids) if existing_metadata is not None else []
            )

            document_ids.append(
                normalized_document_id,
            )

            metadata = AssessmentVectorIndexMetadata(
                assessment_id=normalized_assessment_id,
                document_ids=document_ids,
                indexed_chunk_count=(store.size),
                embedding_provider=embedding_provider,
                embedding_model=embedding_model,
                vector_dimension=store.dimension,
                vector_store_size=store.size,
            )

            self._metadata[normalized_assessment_id] = metadata

            return metadata.model_copy(
                deep=True,
            )

    async def get_store(
        self,
        assessment_id: str,
    ) -> BaseVectorStore:
        """Return the vector store for one assessment."""

        normalized_id = assessment_id.strip()

        if not normalized_id:
            raise DocumentNotFoundError("Assessment index ID cannot be empty.")

        async with self._lock:
            store = self._stores.get(
                normalized_id,
            )

            if store is None:
                raise DocumentNotFoundError(
                    f"Assessment vector index was not found: {normalized_id}."
                )

            return store

    async def get_metadata(
        self,
        assessment_id: str,
    ) -> AssessmentVectorIndexMetadata:
        """Return metadata for one assessment index."""

        normalized_id = assessment_id.strip()

        async with self._lock:
            metadata = self._metadata.get(
                normalized_id,
            )

            if metadata is None:
                raise DocumentNotFoundError(
                    f"Assessment vector index was not found: {normalized_id}."
                )

            return metadata.model_copy(
                deep=True,
            )

    async def contains_document(
        self,
        assessment_id: str,
        document_id: str,
    ) -> bool:
        """Return whether a document is already indexed."""

        normalized_assessment_id = assessment_id.strip()
        normalized_document_id = document_id.strip()

        if not normalized_assessment_id or not normalized_document_id:
            return False

        async with self._lock:
            metadata = self._metadata.get(
                normalized_assessment_id,
            )

            return bool(metadata and normalized_document_id in metadata.document_ids)

    async def clear(self) -> None:
        """Remove all assessment indexes for isolated tests."""

        async with self._lock:
            for store in self._stores.values():
                store.clear()

            self._stores.clear()
            self._metadata.clear()
