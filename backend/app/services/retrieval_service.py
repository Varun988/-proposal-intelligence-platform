from time import perf_counter

from app.core.exceptions import (
    RetrievalConfigurationError,
)
from app.rag.deduplication.base import (
    BaseRetrievalDeduplicator,
)
from app.rag.reranking.base import (
    BaseRetrievalReranker,
)
from app.rag.vector_store.base import BaseVectorStore
from app.schemas.retrieval import (
    RetrievalCandidate,
    RetrievalMetrics,
    RetrievalResponse,
    VectorSearchResponse,
)
from app.services.embedding_service import EmbeddingService


class RetrievalService:
    """Coordinate semantic retrieval, deduplication, and reranking."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: BaseVectorStore,
        deduplicator: BaseRetrievalDeduplicator,
        reranker: BaseRetrievalReranker,
        candidate_limit: int = 20,
        final_limit: int = 5,
    ) -> None:
        self._validate_configuration(
            candidate_limit=candidate_limit,
            final_limit=final_limit,
        )

        if embedding_service.dimension != vector_store.dimension:
            raise RetrievalConfigurationError(
                "Embedding dimension does not match the "
                "vector-store dimension. "
                f"Embedding: {embedding_service.dimension}. "
                f"Vector store: {vector_store.dimension}."
            )

        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._deduplicator = deduplicator
        self._reranker = reranker
        self._candidate_limit = candidate_limit
        self._final_limit = final_limit

    @property
    def candidate_limit(self) -> int:
        """Return the number of candidates requested from vector search."""

        return self._candidate_limit

    @property
    def final_limit(self) -> int:
        """Return the maximum number of final evidence results."""

        return self._final_limit

    def retrieve(
        self,
        query: str,
    ) -> RetrievalResponse:
        """Run the complete retrieval pipeline for one query."""

        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError("Retrieval query cannot be empty.")

        pipeline_started_at = perf_counter()

        embedding_started_at = perf_counter()
        query_embedding = self._embedding_service.embed_query(
            normalized_query,
        )
        embedding_latency_ms = self._elapsed_ms(
            embedding_started_at,
        )

        vector_search_started_at = perf_counter()
        vector_response = self._vector_store.search(
            query=query_embedding,
            limit=self._candidate_limit,
        )
        vector_search_latency_ms = self._elapsed_ms(
            vector_search_started_at,
        )

        candidates = self._convert_vector_results(
            vector_response,
        )

        deduplication_started_at = perf_counter()
        deduplication_result = self._deduplicator.deduplicate(
            candidates,
        )
        deduplication_latency_ms = self._elapsed_ms(
            deduplication_started_at,
        )

        reranking_started_at = perf_counter()
        reranking_result = self._reranker.rerank(
            query=normalized_query,
            candidates=deduplication_result.candidates,
            limit=self._final_limit,
        )
        reranking_latency_ms = self._elapsed_ms(
            reranking_started_at,
        )

        total_latency_ms = self._elapsed_ms(
            pipeline_started_at,
        )

        metrics = RetrievalMetrics(
            initial_candidate_count=len(candidates),
            deduplicated_candidate_count=(deduplication_result.deduplicated_candidate_count),
            duplicate_count=deduplication_result.duplicate_count,
            reranked_candidate_count=(reranking_result.reranked_candidate_count),
            final_result_count=len(
                reranking_result.candidates,
            ),
            embedding_latency_ms=embedding_latency_ms,
            vector_search_latency_ms=vector_search_latency_ms,
            deduplication_latency_ms=deduplication_latency_ms,
            reranking_latency_ms=reranking_latency_ms,
            total_latency_ms=total_latency_ms,
        )

        return RetrievalResponse(
            query=normalized_query,
            candidates=reranking_result.candidates,
            metrics=metrics,
        )

    @staticmethod
    def _convert_vector_results(
        response: VectorSearchResponse,
    ) -> list:
        """Convert vector-store results into retrieval candidates."""

        return [
            RetrievalCandidate(
                chunk=result.chunk,
                retrieval_score=result.score,
                retrieval_rank=result.rank,
                metadata={
                    "vector_search_rank": result.rank,
                    "vector_search_score": result.score,
                },
            )
            for result in response.results
        ]

    @staticmethod
    def _validate_configuration(
        candidate_limit: int,
        final_limit: int,
    ) -> None:
        """Validate retrieval candidate and result limits."""

        if candidate_limit < 1:
            raise RetrievalConfigurationError("candidate_limit must be at least 1.")

        if final_limit < 1:
            raise RetrievalConfigurationError("final_limit must be at least 1.")

        if final_limit > candidate_limit:
            raise RetrievalConfigurationError("final_limit cannot be greater than candidate_limit.")

    @staticmethod
    def _elapsed_ms(
        started_at: float,
    ) -> float:
        """Return elapsed time in milliseconds."""

        return max(
            (perf_counter() - started_at) * 1_000,
            0.0,
        )
