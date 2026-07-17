import asyncio
from typing import Protocol

from app.core.exceptions import (
    DocumentConflictError,
    DocumentNotFoundError,
)
from app.schemas.document_upload import (
    StoredDocumentRecord,
)


class DocumentRepositoryProtocol(Protocol):
    """Persistence contract for document metadata."""

    async def create(
        self,
        record: StoredDocumentRecord,
    ) -> StoredDocumentRecord:
        """Persist a document record."""

    async def get(
        self,
        document_id: str,
    ) -> StoredDocumentRecord:
        """Retrieve a document record."""

    async def update(
        self,
        record: StoredDocumentRecord,
    ) -> StoredDocumentRecord:
        """Replace a document record."""

    async def exists(
        self,
        document_id: str,
    ) -> bool:
        """Return whether a document exists."""


class InMemoryDocumentRepository:
    """Concurrency-safe in-memory document repository."""

    def __init__(self) -> None:
        self._records: dict[
            str,
            StoredDocumentRecord,
        ] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        record: StoredDocumentRecord,
    ) -> StoredDocumentRecord:
        """Persist a new document record."""

        async with self._lock:
            if record.document_id in self._records:
                raise DocumentConflictError(
                    "Document already exists: "
                    f"{record.document_id}."
                )

            stored_record = record.model_copy(
                deep=True,
            )

            self._records[record.document_id] = (
                stored_record
            )

            return stored_record.model_copy(
                deep=True,
            )

    async def get(
        self,
        document_id: str,
    ) -> StoredDocumentRecord:
        """Retrieve one document record."""

        normalized_id = document_id.strip()

        if not normalized_id:
            raise DocumentNotFoundError(
                "Document ID cannot be empty."
            )

        async with self._lock:
            record = self._records.get(
                normalized_id,
            )

            if record is None:
                raise DocumentNotFoundError(
                    "Document not found: "
                    f"{normalized_id}."
                )

            return record.model_copy(
                deep=True,
            )

    async def update(
        self,
        record: StoredDocumentRecord,
    ) -> StoredDocumentRecord:
        """Replace an existing document record."""

        async with self._lock:
            if record.document_id not in self._records:
                raise DocumentNotFoundError(
                    "Document not found: "
                    f"{record.document_id}."
                )

            stored_record = record.model_copy(
                deep=True,
            )

            self._records[record.document_id] = (
                stored_record
            )

            return stored_record.model_copy(
                deep=True,
            )

    async def exists(
        self,
        document_id: str,
    ) -> bool:
        """Return whether a document exists."""

        normalized_id = document_id.strip()

        if not normalized_id:
            return False

        async with self._lock:
            return normalized_id in self._records

    async def clear(self) -> None:
        """Remove all records for isolated tests."""

        async with self._lock:
            self._records.clear()