import asyncio
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Protocol

from app.core.exceptions import (
    DocumentConflictError,
    DocumentNotFoundError,
)
from app.rag.vector_store.base import BaseVectorStore
from app.schemas.document_upload import DocumentPurpose
from app.schemas.embedding import EmbeddedChunk, EmbeddingVector
from app.schemas.retrieval import VectorSearchResponse, VectorSearchResult
from app.schemas.vector_index import AssessmentVectorIndexMetadata


class PurposeScopedVectorStore(BaseVectorStore):
    """Read-only search view over multiple purpose-specific stores."""

    def __init__(self, stores: list[BaseVectorStore]) -> None:
        if not stores:
            raise ValueError("At least one purpose-scoped store is required.")

        dimensions = {store.dimension for store in stores}
        if len(dimensions) != 1:
            raise ValueError(
                "Purpose-scoped vector stores must use one dimension."
            )

        self._stores = list(stores)
        self._dimension = stores[0].dimension

    @property
    def dimension(self) -> int:
        """Return the shared vector dimension."""

        return self._dimension

    @property
    def size(self) -> int:
        """Return the total vectors in the scoped view."""

        return sum(store.size for store in self._stores)

    def add(self, items: list[EmbeddedChunk]) -> None:
        """Reject writes through a read-only scoped view."""

        raise NotImplementedError(
            "Purpose-scoped vector-store views are read-only."
        )

    def search(
        self,
        query: EmbeddingVector,
        limit: int = 5,
    ) -> VectorSearchResponse:
        """Search allowed stores and merge results by vector score."""

        if limit < 1:
            raise ValueError("Search limit must be at least one.")

        candidates: list[VectorSearchResult] = []
        for store in self._stores:
            if store.size == 0:
                continue
            response = store.search(query=query, limit=limit)
            candidates.extend(response.results)

        ranked = sorted(
            candidates,
            key=lambda result: result.score,
            reverse=True,
        )[:limit]

        results = [
            VectorSearchResult(
                chunk=result.chunk,
                score=result.score,
                rank=rank,
            )
            for rank, result in enumerate(ranked, start=1)
        ]

        return VectorSearchResponse(
            results=results,
            query_dimension=query.dimension,
            total_candidates=self.size,
        )

    def save(self, directory: Path) -> None:
        """Reject persistence through a composite read view."""

        raise NotImplementedError(
            "Persist underlying purpose stores individually."
        )

    def clear(self) -> None:
        """Clear every underlying purpose store."""

        for store in self._stores:
            store.clear()


class AssessmentVectorIndexRegistryProtocol(Protocol):
    """Registry contract for assessment and purpose-scoped indexes."""

    async def add_document(
        self,
        assessment_id: str,
        document_id: str,
        items: list[EmbeddedChunk],
        embedding_provider: str,
        embedding_model: str,
        vector_dimension: int,
        document_purpose: DocumentPurpose | str | None = None,
    ) -> AssessmentVectorIndexMetadata:
        """Add one document to its assessment and purpose indexes."""

    async def get_store(
        self,
        assessment_id: str,
        purposes: Iterable[DocumentPurpose | str] | None = None,
    ) -> BaseVectorStore:
        """Return an assessment store, optionally purpose-scoped."""

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
    """Concurrency-safe assessment and purpose-isolated index registry."""

    def __init__(
        self,
        vector_store_factory: Callable[[int], BaseVectorStore],
    ) -> None:
        self._vector_store_factory = vector_store_factory
        self._stores: dict[str, BaseVectorStore] = {}
        self._purpose_stores: dict[
            tuple[str, DocumentPurpose],
            BaseVectorStore,
        ] = {}
        self._metadata: dict[str, AssessmentVectorIndexMetadata] = {}
        self._document_purposes: dict[
            tuple[str, str],
            DocumentPurpose,
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
        document_purpose: DocumentPurpose | str | None = None,
    ) -> AssessmentVectorIndexMetadata:
        """Add one document to global and purpose-specific indexes."""

        normalized_assessment_id = assessment_id.strip()
        normalized_document_id = document_id.strip()

        if not normalized_assessment_id:
            raise ValueError("Assessment ID is required for indexing.")
        if not normalized_document_id:
            raise ValueError("Document ID is required for indexing.")
        if not items:
            raise ValueError("At least one embedded chunk is required.")

        purpose = self._resolve_purpose(
            items=items,
            explicit_purpose=document_purpose,
        )

        async with self._lock:
            existing_metadata = self._metadata.get(
                normalized_assessment_id
            )
            if (
                existing_metadata is not None
                and normalized_document_id in existing_metadata.document_ids
            ):
                raise DocumentConflictError(
                    "Document is already indexed for assessment: "
                    f"{normalized_document_id}."
                )

            global_store = self._stores.get(normalized_assessment_id)
            if global_store is None:
                global_store = self._vector_store_factory(vector_dimension)
                self._stores[normalized_assessment_id] = global_store

            purpose_key = (normalized_assessment_id, purpose)
            purpose_store = self._purpose_stores.get(purpose_key)
            if purpose_store is None:
                purpose_store = self._vector_store_factory(vector_dimension)
                self._purpose_stores[purpose_key] = purpose_store

            for store in (global_store, purpose_store):
                if store.dimension != vector_dimension:
                    raise ValueError(
                        "Assessment index vector dimension does not match "
                        "the embedding dimension."
                    )

            global_store.add(items)
            purpose_store.add(items)

            document_ids = (
                list(existing_metadata.document_ids)
                if existing_metadata is not None
                else []
            )
            document_ids.append(normalized_document_id)
            self._document_purposes[
                (normalized_assessment_id, normalized_document_id)
            ] = purpose

            metadata = AssessmentVectorIndexMetadata(
                assessment_id=normalized_assessment_id,
                document_ids=document_ids,
                indexed_chunk_count=global_store.size,
                embedding_provider=embedding_provider,
                embedding_model=embedding_model,
                vector_dimension=global_store.dimension,
                vector_store_size=global_store.size,
            )
            self._metadata[normalized_assessment_id] = metadata
            return metadata.model_copy(deep=True)

    async def get_store(
        self,
        assessment_id: str,
        purposes: Iterable[DocumentPurpose | str] | None = None,
    ) -> BaseVectorStore:
        """Return the global store or a purpose-scoped search view."""

        normalized_id = assessment_id.strip()
        if not normalized_id:
            raise DocumentNotFoundError(
                "Assessment index ID cannot be empty."
            )

        async with self._lock:
            if purposes is None:
                store = self._stores.get(normalized_id)
                if store is None:
                    raise DocumentNotFoundError(
                        "Assessment vector index was not found: "
                        f"{normalized_id}."
                    )
                return store

            normalized_purposes = {
                self._normalize_purpose(purpose) for purpose in purposes
            }
            if not normalized_purposes:
                raise ValueError(
                    "At least one document purpose is required."
                )

            stores = [
                store
                for purpose in sorted(
                    normalized_purposes,
                    key=lambda value: value.value,
                )
                if (
                    store := self._purpose_stores.get(
                        (normalized_id, purpose)
                    )
                )
                is not None
            ]

            if not stores:
                purpose_values = ", ".join(
                    sorted(purpose.value for purpose in normalized_purposes)
                )
                raise DocumentNotFoundError(
                    "Assessment vector index was not found for purposes: "
                    f"{purpose_values}."
                )

            if len(stores) == 1:
                return stores[0]
            return PurposeScopedVectorStore(stores)

    async def get_metadata(
        self,
        assessment_id: str,
    ) -> AssessmentVectorIndexMetadata:
        """Return metadata for one assessment index."""

        normalized_id = assessment_id.strip()
        async with self._lock:
            metadata = self._metadata.get(normalized_id)
            if metadata is None:
                raise DocumentNotFoundError(
                    "Assessment vector index was not found: "
                    f"{normalized_id}."
                )
            return metadata.model_copy(deep=True)

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
            metadata = self._metadata.get(normalized_assessment_id)
            return bool(
                metadata
                and normalized_document_id in metadata.document_ids
            )

    async def clear(self) -> None:
        """Remove all assessment and purpose indexes."""

        async with self._lock:
            for store in self._stores.values():
                store.clear()
            for store in self._purpose_stores.values():
                store.clear()
            self._stores.clear()
            self._purpose_stores.clear()
            self._metadata.clear()
            self._document_purposes.clear()

    @classmethod
    def _resolve_purpose(
        cls,
        items: list[EmbeddedChunk],
        explicit_purpose: DocumentPurpose | str | None,
    ) -> DocumentPurpose:
        """Resolve and validate one trusted purpose for all chunks."""

        if explicit_purpose is not None:
            purpose = cls._normalize_purpose(explicit_purpose)
        else:
            values = {
                item.chunk.metadata.get("document_purpose")
                for item in items
            }
            if len(values) != 1:
                raise ValueError(
                    "Indexed chunks must share one document purpose."
                )
            raw_purpose = values.pop()
            if not isinstance(raw_purpose, str):
                raise ValueError(
                    "Indexed chunks require document-purpose metadata."
                )
            purpose = cls._normalize_purpose(raw_purpose)

        for item in items:
            chunk_purpose = item.chunk.metadata.get("document_purpose")
            if chunk_purpose is not None and (
                cls._normalize_purpose(chunk_purpose) is not purpose
            ):
                raise ValueError(
                    "Chunk purpose does not match the indexed document."
                )
        return purpose

    @staticmethod
    def _normalize_purpose(
        purpose: DocumentPurpose | str,
    ) -> DocumentPurpose:
        """Normalize one document purpose value."""

        if isinstance(purpose, DocumentPurpose):
            return purpose
        return DocumentPurpose(purpose.strip())
