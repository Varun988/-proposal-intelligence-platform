import asyncio
from typing import Protocol

from app.core.exceptions import (
    DocumentConflictError,
    DocumentNotFoundError,
)
from app.schemas.document import ExtractedDocument


class ExtractedDocumentRepositoryProtocol(Protocol):
    """Persistence contract for extracted documents."""

    async def create(
        self,
        document: ExtractedDocument,
    ) -> ExtractedDocument:
        """Persist one extracted document."""

    async def get(self, document_id: str) -> ExtractedDocument:
        """Retrieve one extracted document."""

    async def exists(self, document_id: str) -> bool:
        """Return whether an extracted document exists."""


class InMemoryExtractedDocumentRepository:
    """Concurrency-safe extracted-document repository."""

    def __init__(self) -> None:
        self._documents: dict[str, ExtractedDocument] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        document: ExtractedDocument,
    ) -> ExtractedDocument:
        """Persist one extracted document."""

        async with self._lock:
            if document.document_id in self._documents:
                raise DocumentConflictError(
                    f"Extracted document already exists: {document.document_id}."
                )
            stored = document.model_copy(deep=True)
            self._documents[document.document_id] = stored
            return stored.model_copy(deep=True)

    async def get(self, document_id: str) -> ExtractedDocument:
        """Retrieve one extracted document."""

        normalized_id = document_id.strip()
        if not normalized_id:
            raise DocumentNotFoundError("Document ID cannot be empty.")

        async with self._lock:
            document = self._documents.get(normalized_id)
            if document is None:
                raise DocumentNotFoundError(f"Extracted document not found: {normalized_id}.")
            return document.model_copy(deep=True)

    async def exists(self, document_id: str) -> bool:
        """Return whether an extracted document exists."""

        normalized_id = document_id.strip()
        if not normalized_id:
            return False
        async with self._lock:
            return normalized_id in self._documents

    async def clear(self) -> None:
        """Remove all extracted documents for isolated tests."""

        async with self._lock:
            self._documents.clear()
