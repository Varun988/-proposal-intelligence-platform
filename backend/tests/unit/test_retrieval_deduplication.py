import pytest

from app.core.exceptions import (
    DeduplicationConfigurationError,
)
from app.rag.deduplication.content import (
    ContentDeduplicator,
)
from app.schemas.chunk import (
    ChunkCitation,
    DocumentChunk,
)
from app.schemas.retrieval import RetrievalCandidate


def create_candidate(
    chunk_id: str,
    text: str,
    score: float,
    rank: int,
    page_number: int = 1,
) -> RetrievalCandidate:
    """Create a synthetic retrieval candidate."""

    return RetrievalCandidate(
        chunk=DocumentChunk(
            chunk_id=chunk_id,
            document_id="document-001",
            text=text,
            page_number=page_number,
            page_chunk_index=rank - 1,
            document_chunk_index=rank - 1,
            citation=ChunkCitation(
                document_id="document-001",
                file_name="synthetic-proposal.pdf",
                page_number=page_number,
                checksum_sha256="a" * 64,
            ),
        ),
        retrieval_score=score,
        retrieval_rank=rank,
    )


def test_deduplicator_removes_exact_duplicates() -> None:
    deduplicator = ContentDeduplicator()

    candidates = [
        create_candidate(
            chunk_id="chunk-001",
            text="The delivery timeline is twelve months.",
            score=0.95,
            rank=1,
        ),
        create_candidate(
            chunk_id="chunk-002",
            text="The delivery timeline is twelve months.",
            score=0.85,
            rank=2,
        ),
    ]

    result = deduplicator.deduplicate(candidates)

    assert result.original_candidate_count == 2
    assert result.deduplicated_candidate_count == 1
    assert result.duplicate_count == 1
    assert result.candidates[0].chunk.chunk_id == "chunk-001"
    assert result.candidates[0].duplicate_chunk_ids == ["chunk-002"]


def test_deduplicator_normalizes_case_and_punctuation() -> None:
    deduplicator = ContentDeduplicator()

    candidates = [
        create_candidate(
            chunk_id="chunk-001",
            text="Delivery Timeline: Twelve Months!",
            score=0.90,
            rank=1,
        ),
        create_candidate(
            chunk_id="chunk-002",
            text="delivery timeline twelve months",
            score=0.80,
            rank=2,
        ),
    ]

    result = deduplicator.deduplicate(candidates)

    assert result.deduplicated_candidate_count == 1
    assert result.duplicate_count == 1


def test_deduplicator_removes_near_duplicates() -> None:
    deduplicator = ContentDeduplicator(
        similarity_threshold=0.75,
    )

    candidates = [
        create_candidate(
            chunk_id="chunk-001",
            text=("The vendor proposes a twelve month implementation delivery timeline."),
            score=0.92,
            rank=1,
        ),
        create_candidate(
            chunk_id="chunk-002",
            text=(
                "The vendor proposes a twelve month "
                "implementation delivery timeline with governance."
            ),
            score=0.82,
            rank=2,
        ),
    ]

    result = deduplicator.deduplicate(candidates)

    assert result.deduplicated_candidate_count == 1
    assert result.duplicate_count == 1


def test_deduplicator_preserves_distinct_evidence() -> None:
    deduplicator = ContentDeduplicator(
        similarity_threshold=0.8,
    )

    candidates = [
        create_candidate(
            chunk_id="delivery",
            text="The delivery timeline is twelve months.",
            score=0.95,
            rank=1,
        ),
        create_candidate(
            chunk_id="security",
            text="All stored customer data is encrypted.",
            score=0.90,
            rank=2,
        ),
    ]

    result = deduplicator.deduplicate(candidates)

    assert result.deduplicated_candidate_count == 2
    assert result.duplicate_count == 0


def test_deduplicator_keeps_highest_scoring_candidate() -> None:
    deduplicator = ContentDeduplicator()

    candidates = [
        create_candidate(
            chunk_id="lower-score",
            text="The support period is three years.",
            score=0.60,
            rank=2,
        ),
        create_candidate(
            chunk_id="higher-score",
            text="The support period is three years.",
            score=0.95,
            rank=1,
        ),
    ]

    result = deduplicator.deduplicate(candidates)

    assert result.candidates[0].chunk.chunk_id == "higher-score"
    assert result.candidates[0].duplicate_chunk_ids == ["lower-score"]


def test_deduplicator_handles_empty_candidates() -> None:
    deduplicator = ContentDeduplicator()

    result = deduplicator.deduplicate([])

    assert result.original_candidate_count == 0
    assert result.deduplicated_candidate_count == 0
    assert result.duplicate_count == 0


@pytest.mark.parametrize(
    ("threshold", "minimum_tokens", "expected_message"),
    [
        (
            -0.1,
            3,
            "similarity_threshold",
        ),
        (
            1.1,
            3,
            "similarity_threshold",
        ),
        (
            0.9,
            0,
            "minimum_token_count",
        ),
    ],
)
def test_deduplicator_rejects_invalid_configuration(
    threshold: float,
    minimum_tokens: int,
    expected_message: str,
) -> None:
    with pytest.raises(
        DeduplicationConfigurationError,
        match=expected_message,
    ):
        ContentDeduplicator(
            similarity_threshold=threshold,
            minimum_token_count=minimum_tokens,
        )
