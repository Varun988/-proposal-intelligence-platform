from pathlib import Path

import pytest

from app.core.exceptions import (
    EmptyVectorStoreError,
    VectorDimensionMismatchError,
    VectorStoreConfigurationError,
)
from app.rag.vector_store.faiss_store import FaissVectorStore
from app.schemas.chunk import (
    ChunkCitation,
    DocumentChunk,
)
from app.schemas.embedding import (
    EmbeddedChunk,
    EmbeddingVector,
)


def create_embedded_chunk(
    chunk_id: str,
    text: str,
    values: list[float],
    chunk_index: int,
) -> EmbeddedChunk:
    """Create an embedded synthetic document chunk."""

    chunk = DocumentChunk(
        chunk_id=chunk_id,
        document_id="document-001",
        text=text,
        page_number=chunk_index + 1,
        page_chunk_index=0,
        document_chunk_index=chunk_index,
        citation=ChunkCitation(
            document_id="document-001",
            file_name="synthetic-proposal.pdf",
            page_number=chunk_index + 1,
            checksum_sha256="a" * 64,
        ),
    )

    return EmbeddedChunk(
        chunk=chunk,
        embedding=EmbeddingVector(
            values=values,
        ),
        provider_name="fake-embeddings",
        model_name="fake-embedding-model",
    )


def create_items() -> list:
    """Create vectors with obvious similarity relationships."""

    return [
        create_embedded_chunk(
            chunk_id="delivery",
            text="The project delivery timeline is twelve months.",
            values=[1.0, 0.0, 0.0],
            chunk_index=0,
        ),
        create_embedded_chunk(
            chunk_id="support",
            text="The vendor provides three years of support.",
            values=[0.0, 1.0, 0.0],
            chunk_index=1,
        ),
        create_embedded_chunk(
            chunk_id="security",
            text="The solution encrypts data at rest.",
            values=[0.0, 0.0, 1.0],
            chunk_index=2,
        ),
    ]


def test_store_adds_embedded_chunks() -> None:
    store = FaissVectorStore(
        dimension=3,
    )

    store.add(create_items())

    assert store.dimension == 3
    assert store.size == 3


def test_store_returns_most_similar_chunk() -> None:
    store = FaissVectorStore(
        dimension=3,
    )
    store.add(create_items())

    response = store.search(
        query=EmbeddingVector(
            values=[0.9, 0.1, 0.0],
        ),
        limit=2,
    )

    assert len(response.results) == 2
    assert response.results[0].chunk.chunk_id == "delivery"
    assert response.results[0].rank == 1
    assert response.results[0].score > response.results[1].score
    assert response.query_dimension == 3
    assert response.total_candidates == 3


def test_store_limits_results_to_available_items() -> None:
    store = FaissVectorStore(
        dimension=3,
    )
    store.add(create_items())

    response = store.search(
        query=EmbeddingVector(
            values=[1.0, 0.0, 0.0],
        ),
        limit=10,
    )

    assert len(response.results) == 3


def test_store_rejects_invalid_embedding_dimension() -> None:
    store = FaissVectorStore(
        dimension=3,
    )

    invalid_item = create_embedded_chunk(
        chunk_id="invalid",
        text="Invalid vector.",
        values=[1.0, 2.0],
        chunk_index=0,
    )

    with pytest.raises(
        VectorDimensionMismatchError,
        match="Embedding dimension",
    ):
        store.add([invalid_item])


def test_store_rejects_invalid_query_dimension() -> None:
    store = FaissVectorStore(
        dimension=3,
    )
    store.add(create_items())

    with pytest.raises(
        VectorDimensionMismatchError,
        match="Query vector dimension",
    ):
        store.search(
            query=EmbeddingVector(
                values=[1.0, 2.0],
            )
        )


def test_store_rejects_search_when_empty() -> None:
    store = FaissVectorStore(
        dimension=3,
    )

    with pytest.raises(
        EmptyVectorStoreError,
        match="empty vector store",
    ):
        store.search(
            query=EmbeddingVector(
                values=[1.0, 0.0, 0.0],
            )
        )


def test_store_rejects_invalid_search_limit() -> None:
    store = FaissVectorStore(
        dimension=3,
    )
    store.add(create_items())

    with pytest.raises(
        VectorStoreConfigurationError,
        match="Search limit",
    ):
        store.search(
            query=EmbeddingVector(
                values=[1.0, 0.0, 0.0],
            ),
            limit=0,
        )


def test_store_clears_index() -> None:
    store = FaissVectorStore(
        dimension=3,
    )
    store.add(create_items())

    store.clear()

    assert store.size == 0


def test_store_saves_index_and_metadata(
    tmp_path: Path,
) -> None:
    store = FaissVectorStore(
        dimension=3,
    )
    store.add(create_items())

    store.save(tmp_path)

    assert (tmp_path / "index.faiss").exists()
    assert (tmp_path / "metadata.json").exists()


def test_store_rejects_invalid_dimension() -> None:
    with pytest.raises(
        VectorStoreConfigurationError,
        match="dimension must be at least 1",
    ):
        FaissVectorStore(
            dimension=0,
        )
