import pytest

from app.core.exceptions import (
    RerankingConfigurationError,
)
from app.rag.reranking.lexical import (
    LexicalRetrievalReranker,
)
from app.schemas.chunk import (
    ChunkCitation,
    DocumentChunk,
)
from app.schemas.retrieval import RetrievalCandidate


def create_candidate(
    chunk_id: str,
    text: str,
    retrieval_score: float,
    retrieval_rank: int,
) -> RetrievalCandidate:
    """Create a synthetic candidate for reranking tests."""

    return RetrievalCandidate(
        chunk=DocumentChunk(
            chunk_id=chunk_id,
            document_id="document-001",
            text=text,
            page_number=retrieval_rank,
            page_chunk_index=0,
            document_chunk_index=retrieval_rank - 1,
            citation=ChunkCitation(
                document_id="document-001",
                file_name="synthetic-proposal.pdf",
                page_number=retrieval_rank,
                checksum_sha256="a" * 64,
            ),
        ),
        retrieval_score=retrieval_score,
        retrieval_rank=retrieval_rank,
    )


def test_reranker_prioritizes_lexically_relevant_candidate() -> None:
    reranker = LexicalRetrievalReranker(
        retrieval_weight=0.4,
        lexical_weight=0.6,
    )

    candidates = [
        create_candidate(
            chunk_id="generic",
            text="The vendor provided a detailed proposal.",
            retrieval_score=0.95,
            retrieval_rank=1,
        ),
        create_candidate(
            chunk_id="delivery",
            text=("The project delivery timeline is twelve months."),
            retrieval_score=0.80,
            retrieval_rank=2,
        ),
    ]

    result = reranker.rerank(
        query="What is the project delivery timeline?",
        candidates=candidates,
    )

    assert result.candidates[0].chunk.chunk_id == "delivery"
    assert result.candidates[0].reranking_score is not None
    assert result.candidates[0].final_score is not None


def test_reranker_preserves_original_retrieval_data() -> None:
    reranker = LexicalRetrievalReranker()

    candidate = create_candidate(
        chunk_id="delivery",
        text="The delivery timeline is twelve months.",
        retrieval_score=0.91,
        retrieval_rank=2,
    )

    result = reranker.rerank(
        query="delivery timeline",
        candidates=[candidate],
    )

    reranked = result.candidates[0]

    assert reranked.retrieval_score == 0.91
    assert reranked.retrieval_rank == 2
    assert reranked.chunk.citation.label == ("synthetic-proposal.pdf, page 2")


def test_reranker_applies_result_limit() -> None:
    reranker = LexicalRetrievalReranker()

    candidates = [
        create_candidate(
            chunk_id=f"chunk-{index}",
            text=f"Delivery timeline evidence {index}.",
            retrieval_score=1.0 - index * 0.1,
            retrieval_rank=index + 1,
        )
        for index in range(5)
    ]

    result = reranker.rerank(
        query="delivery timeline",
        candidates=candidates,
        limit=2,
    )

    assert result.original_candidate_count == 5
    assert result.reranked_candidate_count == 2


def test_reranker_handles_equal_retrieval_scores() -> None:
    reranker = LexicalRetrievalReranker()

    candidates = [
        create_candidate(
            chunk_id="support",
            text="The support duration is three years.",
            retrieval_score=0.8,
            retrieval_rank=1,
        ),
        create_candidate(
            chunk_id="delivery",
            text="The delivery timeline is twelve months.",
            retrieval_score=0.8,
            retrieval_rank=2,
        ),
    ]

    result = reranker.rerank(
        query="delivery timeline",
        candidates=candidates,
    )

    assert result.candidates[0].chunk.chunk_id == "delivery"


def test_reranker_handles_empty_candidate_collection() -> None:
    reranker = LexicalRetrievalReranker()

    result = reranker.rerank(
        query="delivery timeline",
        candidates=[],
    )

    assert result.original_candidate_count == 0
    assert result.reranked_candidate_count == 0


@pytest.mark.parametrize(
    "query",
    [
        "",
        "   ",
    ],
)
def test_reranker_rejects_empty_query(
    query: str,
) -> None:
    reranker = LexicalRetrievalReranker()

    with pytest.raises(
        ValueError,
        match="Reranking query cannot be empty",
    ):
        reranker.rerank(
            query=query,
            candidates=[],
        )


def test_reranker_rejects_query_without_searchable_terms() -> None:
    reranker = LexicalRetrievalReranker()

    with pytest.raises(
        ValueError,
        match="searchable terms",
    ):
        reranker.rerank(
            query="!!!",
            candidates=[
                create_candidate(
                    chunk_id="chunk-001",
                    text="Synthetic evidence.",
                    retrieval_score=0.9,
                    retrieval_rank=1,
                )
            ],
        )


@pytest.mark.parametrize(
    (
        "retrieval_weight",
        "lexical_weight",
        "expected_message",
    ),
    [
        (
            -0.1,
            1.1,
            "retrieval_weight",
        ),
        (
            0.5,
            -0.1,
            "lexical_weight",
        ),
        (
            0.7,
            0.4,
            "must add up to 1",
        ),
    ],
)
def test_reranker_rejects_invalid_weights(
    retrieval_weight: float,
    lexical_weight: float,
    expected_message: str,
) -> None:
    with pytest.raises(
        RerankingConfigurationError,
        match=expected_message,
    ):
        LexicalRetrievalReranker(
            retrieval_weight=retrieval_weight,
            lexical_weight=lexical_weight,
        )


def test_reranker_rejects_invalid_limit() -> None:
    reranker = LexicalRetrievalReranker()

    with pytest.raises(
        RerankingConfigurationError,
        match="limit must be at least 1",
    ):
        reranker.rerank(
            query="delivery timeline",
            candidates=[],
            limit=0,
        )
