from pathlib import Path

import pytest

from app.core.exceptions import EmbeddingDimensionError
from app.schemas.chunk import (
    ChunkCitation,
    DocumentChunk,
)
from app.services.embedding_service import EmbeddingService
from tests.embedding_fakes import (
    FakeEmbeddingProvider,
    InvalidDimensionEmbeddingProvider,
)


def create_chunk(
    chunk_id: str,
    text: str,
    chunk_index: int,
) -> DocumentChunk:
    """Create a synthetic document chunk for embedding tests."""

    return DocumentChunk(
        chunk_id=chunk_id,
        document_id="document-001",
        text=text,
        page_number=1,
        page_chunk_index=chunk_index,
        document_chunk_index=chunk_index,
        citation=ChunkCitation(
            document_id="document-001",
            file_name="synthetic-proposal.pdf",
            page_number=1,
            checksum_sha256="a" * 64,
        ),
        metadata={
            "source_path": str(Path("/tmp/synthetic-proposal.pdf")),
        },
    )


def test_service_embeds_document_chunks() -> None:
    provider = FakeEmbeddingProvider(
        dimension=3,
    )
    service = EmbeddingService(provider)

    chunks = [
        create_chunk(
            chunk_id="chunk-001",
            text="The delivery period is twelve months.",
            chunk_index=0,
        ),
        create_chunk(
            chunk_id="chunk-002",
            text="The support period is three years.",
            chunk_index=1,
        ),
    ]

    result = service.embed_chunks(chunks)

    assert result.item_count == 2
    assert result.dimension == 3
    assert result.provider_name == "fake-embeddings"
    assert result.model_name == "fake-embedding-model"

    assert result.items[0].chunk.chunk_id == "chunk-001"
    assert result.items[0].embedding.dimension == 3

    assert provider.received_document_texts == [
        "The delivery period is twelve months.",
        "The support period is three years.",
    ]


def test_service_embeds_search_query() -> None:
    provider = FakeEmbeddingProvider(
        dimension=3,
    )
    service = EmbeddingService(provider)

    vector = service.embed_query("What is the delivery timeline?")

    assert vector.dimension == 3
    assert provider.received_queries == ["What is the delivery timeline?"]


def test_service_rejects_empty_query() -> None:
    service = EmbeddingService(
        FakeEmbeddingProvider(),
    )

    with pytest.raises(
        ValueError,
        match="Search query cannot be empty",
    ):
        service.embed_query("   ")


def test_service_handles_empty_chunk_collection() -> None:
    service = EmbeddingService(
        FakeEmbeddingProvider(
            dimension=3,
        )
    )

    result = service.embed_chunks([])

    assert result.item_count == 0
    assert result.dimension == 3
    assert result.items == []


def test_service_exposes_provider_properties() -> None:
    service = EmbeddingService(
        FakeEmbeddingProvider(
            dimension=5,
        )
    )

    assert service.provider_name == "fake-embeddings"
    assert service.model_name == "fake-embedding-model"
    assert service.dimension == 5


def test_service_rejects_invalid_document_dimension() -> None:
    provider = InvalidDimensionEmbeddingProvider(
        dimension=3,
    )
    service = EmbeddingService(provider)

    chunk = create_chunk(
        chunk_id="chunk-001",
        text="Synthetic proposal content.",
        chunk_index=0,
    )

    with pytest.raises(
        EmbeddingDimensionError,
        match="unexpected dimension",
    ):
        service.embed_chunks([chunk])


def test_service_rejects_invalid_query_dimension() -> None:
    provider = InvalidDimensionEmbeddingProvider(
        dimension=3,
    )
    service = EmbeddingService(provider)

    with pytest.raises(
        EmbeddingDimensionError,
        match="unexpected dimension",
    ):
        service.embed_query("What is the delivery timeline?")
