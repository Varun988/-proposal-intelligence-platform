from abc import ABC, abstractmethod

from app.schemas.retrieval import (
    RerankingResult,
    RetrievalCandidate,
)


class BaseRetrievalReranker(ABC):
    """Contract implemented by retrieval rerankers."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        candidates: list[RetrievalCandidate],
        limit: int | None = None,
    ) -> RerankingResult:
        """Rerank candidates according to query relevance."""