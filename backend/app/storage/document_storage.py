import asyncio
from typing import Protocol

from app.core.exceptions import (
    DocumentNotFoundError,
    DocumentStorageError,
)


class DocumentStorageProtocol(Protocol):
    """Binary storage contract for uploaded documents."""

    async def save(
        self,
        storage_file_name: str,
        content: bytes,
    ) -> None:
        """Store binary document content."""

    async def read(
        self,
        storage_file_name: str,
    ) -> bytes:
        """Read binary document content."""

    async def delete(
        self,
        storage_file_name: str,
    ) -> None:
        """Delete binary document content."""


class InMemoryDocumentStorage:
    """Concurrency-safe in-memory binary storage."""

    def __init__(self) -> None:
        self._documents: dict[str, bytes] = {}
        self._lock = asyncio.Lock()

    async def save(
        self,
        storage_file_name: str,
        content: bytes,
    ) -> None:
        """Store document bytes using a generated name."""

        normalized_name = storage_file_name.strip()

        if not normalized_name:
            raise DocumentStorageError("Storage filename cannot be empty.")

        if not content:
            raise DocumentStorageError("Stored document content cannot be empty.")

        async with self._lock:
            if normalized_name in self._documents:
                raise DocumentStorageError("Stored document already exists.")

            self._documents[normalized_name] = bytes(content)

    async def read(
        self,
        storage_file_name: str,
    ) -> bytes:
        """Read stored document bytes."""

        normalized_name = storage_file_name.strip()

        async with self._lock:
            content = self._documents.get(normalized_name)

            if content is None:
                raise DocumentNotFoundError("Stored document content was not found.")

            return bytes(content)

    async def delete(
        self,
        storage_file_name: str,
    ) -> None:
        """Delete stored document bytes."""

        normalized_name = storage_file_name.strip()

        async with self._lock:
            if normalized_name not in self._documents:
                raise DocumentNotFoundError("Stored document content was not found.")

            del self._documents[normalized_name]

    async def clear(self) -> None:
        """Remove all stored content for isolated tests."""

        async with self._lock:
            self._documents.clear()
