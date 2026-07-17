import pytest

from app.core.exceptions import (
    DocumentConflictError,
    DocumentNotFoundError,
)
from app.repositories.document_chunk import (
    InMemoryDocumentChunkRepository,
)
from app.schemas.chunk import (
    ChunkCitation,
    ChunkingResult,
    DocumentChunk,
)


def create_result() -> ChunkingResult:
    """Create one synthetic chunking result."""

    chunk = DocumentChunk(
        chunk_id="chunk-001",
        document_id="document-001",
        text="Synthetic proposal content.",
        page_number=1,
        page_chunk_index=0,
        document_chunk_index=0,
        citation=ChunkCitation(
            document_id="document-001",
            file_name="proposal.txt",
            page_number=1,
            checksum_sha256="a" * 64,
        ),
    )

    return ChunkingResult(
        document_id="document-001",
        chunks=[chunk],
        source_character_count=27,
        chunk_character_count=27,
    )


@pytest.mark.asyncio
async def test_repository_persists_chunks() -> None:
    repository = InMemoryDocumentChunkRepository()

    created = await repository.create(
        create_result(),
    )

    retrieved = await repository.get_result(
        created.document_id,
    )

    assert retrieved == created
    assert retrieved is not created
    assert retrieved.chunk_count == 1


@pytest.mark.asyncio
async def test_repository_returns_deep_copies() -> None:
    repository = InMemoryDocumentChunkRepository()

    await repository.create(
        create_result(),
    )

    chunks = await repository.get_chunks(
        "document-001",
    )

    chunks[0].text = "Changed text."

    stored_chunks = await repository.get_chunks(
        "document-001",
    )

    assert stored_chunks[0].text == "Synthetic proposal content."


@pytest.mark.asyncio
async def test_repository_rejects_duplicate_document() -> None:
    repository = InMemoryDocumentChunkRepository()
    result = create_result()

    await repository.create(result)

    with pytest.raises(
        DocumentConflictError,
        match="already exist",
    ):
        await repository.create(result)


@pytest.mark.asyncio
async def test_repository_rejects_unknown_document() -> None:
    repository = InMemoryDocumentChunkRepository()

    with pytest.raises(
        DocumentNotFoundError,
        match="not found",
    ):
        await repository.get_chunks(
            "document-missing",
        )
