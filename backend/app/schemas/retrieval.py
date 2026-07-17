from pydantic import BaseModel, Field, computed_field

from app.schemas.chunk import DocumentChunk


class VectorSearchResult(BaseModel):
    """One document chunk returned by vector similarity search."""

    chunk: DocumentChunk
    score: float
    rank: int = Field(ge=1)


class VectorSearchResponse(BaseModel):
    """Ranked results returned for one vector query."""

    results: list[VectorSearchResult]
    query_dimension: int = Field(ge=1)
    total_candidates: int = Field(ge=0)


class RetrievalCandidate(BaseModel):
    """A candidate passing through the retrieval pipeline."""

    chunk: DocumentChunk
    retrieval_score: float
    retrieval_rank: int = Field(ge=1)

    reranking_score: float | None = None
    final_score: float | None = None

    duplicate_chunk_ids: list[str] = Field(
        default_factory=list,
    )

    metadata: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict,
    )

    @computed_field
    @property
    def citation_label(self) -> str:
        """Return the source citation for the candidate."""

        return self.chunk.citation.label

    @computed_field
    @property
    def duplicate_count(self) -> int:
        """Return the number of duplicates merged into this candidate."""

        return len(self.duplicate_chunk_ids)


class DeduplicationResult(BaseModel):
    """Result produced by a retrieval deduplication stage."""

    candidates: list[RetrievalCandidate]
    original_candidate_count: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)

    @computed_field
    @property
    def deduplicated_candidate_count(self) -> int:
        """Return the number of candidates remaining after deduplication."""

        return len(self.candidates)


class RerankingResult(BaseModel):
    """Result produced by a retrieval reranking stage."""

    candidates: list[RetrievalCandidate]
    original_candidate_count: int = Field(ge=0)

    @computed_field
    @property
    def reranked_candidate_count(self) -> int:
        """Return the number of reranked candidates."""

        return len(self.candidates)


class RetrievalMetrics(BaseModel):
    """Execution metrics captured for one retrieval pipeline run."""

    initial_candidate_count: int = Field(ge=0)
    deduplicated_candidate_count: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)
    reranked_candidate_count: int = Field(ge=0)
    final_result_count: int = Field(ge=0)

    embedding_latency_ms: float = Field(ge=0)
    vector_search_latency_ms: float = Field(ge=0)
    deduplication_latency_ms: float = Field(ge=0)
    reranking_latency_ms: float = Field(ge=0)
    total_latency_ms: float = Field(ge=0)


class RetrievalResponse(BaseModel):
    """Final evidence and metrics returned by the retrieval pipeline."""

    query: str
    candidates: list[RetrievalCandidate]
    metrics: RetrievalMetrics

    @computed_field
    @property
    def result_count(self) -> int:
        """Return the number of final retrieval candidates."""

        return len(self.candidates)
