import asyncio
from typing import Protocol

from app.core.exceptions import (
    DocumentConflictError,
    DocumentNotFoundError,
)
from app.schemas.chunk import (
    ChunkingResult,
)


class DocumentChunkRepositoryProtocol(Protocol):
    """Persistence contract for document chunks."""

    async def create(
        self,
        result: ChunkingResult,
    ) -> ChunkingResult:
        """Persist one document's chunking result."""

    async def get_result(
        self,
        document_id: str,
    ) -> ChunkingResult:
        """Retrieve one document's chunking result."""

    async def get_chunks(
        self,
        document_id: str,
    ) -> list:
        """Retrieve chunks belonging to one document."""

    async def exists(
        self,
        document_id: str,
    ) -> bool:
        """Return whether chunks exist for a document."""


class InMemoryDocumentChunkRepository:
    """Concurrency-safe in-memory document chunk repository."""

    def __init__(self) -> None:
        self._results: dict[str, ChunkingResult] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        result: ChunkingResult,
    ) -> ChunkingResult:
        """Persist one document's chunking result."""

        async with self._lock:
            if result.document_id in self._results:
                raise DocumentConflictError(f"Document chunks already exist: {result.document_id}.")

            stored_result = result.model_copy(
                deep=True,
            )

            self._results[result.document_id] = stored_result

            return stored_result.model_copy(
                deep=True,
            )

    async def get_result(
        self,
        document_id: str,
    ) -> ChunkingResult:
        """Retrieve one document's chunking result."""

        normalized_id = document_id.strip()

        if not normalized_id:
            raise DocumentNotFoundError("Document ID cannot be empty.")

        async with self._lock:
            result = self._results.get(
                normalized_id,
            )

            if result is None:
                raise DocumentNotFoundError(f"Document chunks were not found: {normalized_id}.")

            return result.model_copy(
                deep=True,
            )

    async def get_chunks(
        self,
        document_id: str,
    ) -> list:
        """Retrieve chunks belonging to one document."""

        result = await self.get_result(
            document_id,
        )

        return [chunk.model_copy(deep=True) for chunk in result.chunks]

    async def exists(
        self,
        document_id: str,
    ) -> bool:
        """Return whether chunks exist for a document."""

        normalized_id = document_id.strip()

        if not normalized_id:
            return False

        async with self._lock:
            return normalized_id in self._results

    async def clear(self) -> None:
        """Remove all stored chunks for isolated tests."""

        async with self._lock:
            self._results.clear()
