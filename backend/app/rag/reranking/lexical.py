import math
import re
from collections import Counter

from app.core.exceptions import (
    RerankingConfigurationError,
)
from app.rag.reranking.base import BaseRetrievalReranker
from app.schemas.retrieval import (
    RerankingResult,
    RetrievalCandidate,
)


class LexicalRetrievalReranker(BaseRetrievalReranker):
    """Rerank retrieval candidates using lexical query relevance."""

    def __init__(
        self,
        retrieval_weight: float = 0.7,
        lexical_weight: float = 0.3,
    ) -> None:
        self._validate_weights(
            retrieval_weight=retrieval_weight,
            lexical_weight=lexical_weight,
        )

        self._retrieval_weight = retrieval_weight
        self._lexical_weight = lexical_weight

    @property
    def retrieval_weight(self) -> float:
        """Return the retrieval-score weight."""

        return self._retrieval_weight

    @property
    def lexical_weight(self) -> float:
        """Return the lexical-score weight."""

        return self._lexical_weight

    def rerank(
        self,
        query: str,
        candidates: list[RetrievalCandidate],
        limit: int | None = None,
    ) -> RerankingResult:
        """Rerank candidates using retrieval and lexical scores."""

        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError("Reranking query cannot be empty.")

        if limit is not None and limit < 1:
            raise RerankingConfigurationError("Reranking limit must be at least 1.")

        if not candidates:
            return RerankingResult(
                candidates=[],
                original_candidate_count=0,
            )

        query_tokens = self._tokenize(normalized_query)

        if not query_tokens:
            raise ValueError("Reranking query must contain searchable terms.")

        reranked_candidates: list[RetrievalCandidate] = []

        for candidate in candidates:
            normalized_retrieval_score = (
                self._normalize_retrieval_score(
                    candidate.retrieval_score,
                )
            )

            lexical_score = self._calculate_lexical_score(
                query_tokens=query_tokens,
                candidate_text=candidate.chunk.text,
            )

            final_score = (
                normalized_retrieval_score * self._retrieval_weight
                + lexical_score * self._lexical_weight
            )

            reranked_candidate = candidate.model_copy(
                deep=True,
                update={
                    "reranking_score": lexical_score,
                    "final_score": final_score,
                    "metadata": {
                        **candidate.metadata,
                        "normalized_retrieval_score": (normalized_retrieval_score),
                        "lexical_score": lexical_score,
                    },
                },
            )

            reranked_candidates.append(
                reranked_candidate,
            )

        reranked_candidates.sort(
            key=lambda candidate: (
                -(candidate.final_score if candidate.final_score is not None else float("-inf")),
                candidate.retrieval_rank,
            )
        )

        if limit is not None:
            reranked_candidates = reranked_candidates[:limit]

        return RerankingResult(
            candidates=reranked_candidates,
            original_candidate_count=len(candidates),
        )

    @staticmethod
    def _normalize_retrieval_score(
        score: float,
    ) -> float:
        """Normalize cosine similarity from minus one to one."""

        bounded_score = max(
            -1.0,
            min(score, 1.0),
        )

        return (bounded_score + 1.0) / 2.0

    @staticmethod
    def _calculate_lexical_score(
        query_tokens: list[str],
        candidate_text: str,
    ) -> float:
        """Calculate token-overlap relevance with term frequency."""

        candidate_tokens = LexicalRetrievalReranker._tokenize(
            candidate_text,
        )

        if not candidate_tokens:
            return 0.0

        query_counts = Counter(query_tokens)
        candidate_counts = Counter(candidate_tokens)

        matched_weight = sum(
            min(
                query_count,
                candidate_counts.get(token, 0),
            )
            for token, query_count in query_counts.items()
        )

        total_query_weight = sum(query_counts.values())

        if total_query_weight == 0:
            return 0.0

        return matched_weight / total_query_weight

    @staticmethod
    def _tokenize(text: str) -> list:
        """Convert text into normalized searchable terms."""

        return re.findall(
            r"\b\w+\b",
            text.casefold(),
        )

    @staticmethod
    def _validate_weights(
        retrieval_weight: float,
        lexical_weight: float,
    ) -> None:
        """Validate reranking score weights."""

        if not 0.0 <= retrieval_weight <= 1.0:
            raise RerankingConfigurationError("retrieval_weight must be between 0 and 1.")

        if not 0.0 <= lexical_weight <= 1.0:
            raise RerankingConfigurationError("lexical_weight must be between 0 and 1.")

        total_weight = retrieval_weight + lexical_weight

        if not math.isclose(
            total_weight,
            1.0,
            abs_tol=1e-9,
        ):
            raise RerankingConfigurationError("Reranking weights must add up to 1.")
