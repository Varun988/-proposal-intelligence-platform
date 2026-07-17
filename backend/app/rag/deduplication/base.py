from abc import ABC, abstractmethod

from app.schemas.retrieval import (
    DeduplicationResult,
    RetrievalCandidate,
)


class BaseRetrievalDeduplicator(ABC):
    """Contract implemented by retrieval deduplicators."""

    @abstractmethod
    def deduplicate(
        self,
        candidates: list[RetrievalCandidate],
    ) -> DeduplicationResult:
        """Remove duplicate retrieval candidates."""
