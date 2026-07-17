import pytest

from app.core.exceptions import (
    RetrievalConfigurationError,
)
from app.rag.deduplication.content import (
    ContentDeduplicator,
)
from app.rag.reranking.lexical import (
    LexicalRetrievalReranker,
)
from app.rag.vector_store.faiss_store import (
    FaissVectorStore,
)
from app.schemas.chunk import (
    ChunkCitation,
    DocumentChunk,
)
from app.schemas.embedding import (
    EmbeddedChunk,
    EmbeddingVector,
)
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from tests.embedding_fakes import FakeEmbeddingProvider


def create_embedded_chunk(
    chunk_id: str,
    text: str,
    values: list[float],
    page_number: int,
) -> EmbeddedChunk:
    """Create an embedded synthetic evidence chunk."""

    chunk = DocumentChunk(
        chunk_id=chunk_id,
        document_id="document-001",
        text=text,
        page_number=page_number,
        page_chunk_index=0,
        document_chunk_index=page_number - 1,
        citation=ChunkCitation(
            document_id="document-001",
            file_name="synthetic-proposal.pdf",
            page_number=page_number,
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


def create_retrieval_service(
    candidate_limit: int = 5,
    final_limit: int = 3,
) -> RetrievalService:
    """Create a retrieval pipeline with deterministic test components."""

    embedding_service = EmbeddingService(
        FakeEmbeddingProvider(
            dimension=3,
        )
    )

    vector_store = FaissVectorStore(
        dimension=3,
    )

    vector_store.add(
        [
            create_embedded_chunk(
                chunk_id="delivery-primary",
                text=("The project delivery timeline is twelve months."),
                values=[1.0, 0.0, 0.0],
                page_number=1,
            ),
            create_embedded_chunk(
                chunk_id="delivery-duplicate",
                text=("The project delivery timeline is twelve months."),
                values=[0.99, -0.01, 0.0],
                page_number=2,
            ),
            create_embedded_chunk(
                chunk_id="support",
                text=("The vendor provides three years of support."),
                values=[0.0, 1.0, 0.0],
                page_number=3,
            ),
            create_embedded_chunk(
                chunk_id="security",
                text="Customer data is encrypted at rest.",
                values=[0.0, 0.0, 1.0],
                page_number=4,
            ),
        ]
    )

    return RetrievalService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        deduplicator=ContentDeduplicator(),
        reranker=LexicalRetrievalReranker(
            retrieval_weight=0.3,
            lexical_weight=0.7,
        ),
        candidate_limit=candidate_limit,
        final_limit=final_limit,
    )


def test_service_executes_complete_retrieval_pipeline() -> None:
    service = create_retrieval_service()

    response = service.retrieve("What is the project delivery timeline?")

    assert response.query == ("What is the project delivery timeline?")
    assert response.result_count == 3

    assert response.candidates[0].chunk.chunk_id == "delivery-primary"

    assert response.candidates[0].citation_label == ("synthetic-proposal.pdf, page 1")

    assert response.candidates[0].final_score is not None
    assert response.candidates[0].reranking_score is not None


def test_service_reports_stage_counts() -> None:
    service = create_retrieval_service()

    response = service.retrieve("project delivery timeline")

    assert response.metrics.initial_candidate_count == 4
    assert response.metrics.deduplicated_candidate_count == 3
    assert response.metrics.duplicate_count == 1
    assert response.metrics.reranked_candidate_count == 3
    assert response.metrics.final_result_count == 3


def test_service_preserves_duplicate_traceability() -> None:
    service = create_retrieval_service()

    response = service.retrieve("project delivery timeline")

    delivery_candidate = next(
        candidate
        for candidate in response.candidates
        if candidate.chunk.chunk_id == "delivery-primary"
    )

    assert delivery_candidate.duplicate_chunk_ids == ["delivery-duplicate"]
    assert delivery_candidate.duplicate_count == 1


def test_service_records_non_negative_latency() -> None:
    service = create_retrieval_service()

    response = service.retrieve("project delivery timeline")

    metrics = response.metrics

    assert metrics.embedding_latency_ms >= 0
    assert metrics.vector_search_latency_ms >= 0
    assert metrics.deduplication_latency_ms >= 0
    assert metrics.reranking_latency_ms >= 0
    assert metrics.total_latency_ms >= 0


def test_service_applies_final_result_limit() -> None:
    service = create_retrieval_service(
        candidate_limit=4,
        final_limit=2,
    )

    response = service.retrieve("project delivery timeline")

    assert response.result_count == 2
    assert response.metrics.final_result_count == 2


@pytest.mark.parametrize(
    "query",
    [
        "",
        "   ",
    ],
)
def test_service_rejects_empty_query(
    query: str,
) -> None:
    service = create_retrieval_service()

    with pytest.raises(
        ValueError,
        match="Retrieval query cannot be empty",
    ):
        service.retrieve(query)


@pytest.mark.parametrize(
    (
        "candidate_limit",
        "final_limit",
        "expected_message",
    ),
    [
        (
            0,
            1,
            "candidate_limit",
        ),
        (
            5,
            0,
            "final_limit must be at least 1",
        ),
        (
            5,
            6,
            "final_limit cannot be greater",
        ),
    ],
)
def test_service_rejects_invalid_limits(
    candidate_limit: int,
    final_limit: int,
    expected_message: str,
) -> None:
    with pytest.raises(
        RetrievalConfigurationError,
        match=expected_message,
    ):
        create_retrieval_service(
            candidate_limit=candidate_limit,
            final_limit=final_limit,
        )


def test_service_rejects_dimension_mismatch() -> None:
    embedding_service = EmbeddingService(
        FakeEmbeddingProvider(
            dimension=3,
        )
    )
    vector_store = FaissVectorStore(
        dimension=4,
    )

    with pytest.raises(
        RetrievalConfigurationError,
        match="Embedding dimension does not match",
    ):
        RetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
            deduplicator=ContentDeduplicator(),
            reranker=LexicalRetrievalReranker(),
        )
