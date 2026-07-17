import hashlib
import re

from app.core.exceptions import (
    DeduplicationConfigurationError,
)
from app.rag.deduplication.base import (
    BaseRetrievalDeduplicator,
)
from app.schemas.retrieval import (
    DeduplicationResult,
    RetrievalCandidate,
)


class ContentDeduplicator(BaseRetrievalDeduplicator):
    """Remove exact and near-duplicate retrieval candidates."""

    def __init__(
        self,
        similarity_threshold: float = 0.9,
        minimum_token_count: int = 3,
    ) -> None:
        if not 0.0 <= similarity_threshold <= 1.0:
            raise DeduplicationConfigurationError("similarity_threshold must be between 0 and 1.")

        if minimum_token_count < 1:
            raise DeduplicationConfigurationError("minimum_token_count must be at least 1.")

        self._similarity_threshold = similarity_threshold
        self._minimum_token_count = minimum_token_count

    @property
    def similarity_threshold(self) -> float:
        """Return the near-duplicate similarity threshold."""

        return self._similarity_threshold

    def deduplicate(
        self,
        candidates: list[RetrievalCandidate],
    ) -> DeduplicationResult:
        """Keep the strongest candidate from each duplicate group."""

        if not candidates:
            return DeduplicationResult(
                candidates=[],
                original_candidate_count=0,
                duplicate_count=0,
            )

        ordered_candidates = sorted(
            candidates,
            key=lambda candidate: (
                -candidate.retrieval_score,
                candidate.retrieval_rank,
            ),
        )

        retained_candidates: list[RetrievalCandidate] = []
        exact_hashes: dict[str, RetrievalCandidate] = {}
        duplicate_count = 0

        for candidate in ordered_candidates:
            normalized_text = self._normalize_text(
                candidate.chunk.text,
            )
            content_hash = self._calculate_content_hash(
                normalized_text,
            )

            exact_match = exact_hashes.get(content_hash)

            if exact_match is not None:
                self._record_duplicate(
                    retained=exact_match,
                    duplicate=candidate,
                )
                duplicate_count += 1
                continue

            near_match = self._find_near_duplicate(
                candidate=candidate,
                retained_candidates=retained_candidates,
            )

            if near_match is not None:
                self._record_duplicate(
                    retained=near_match,
                    duplicate=candidate,
                )
                duplicate_count += 1
                continue

            retained_candidates.append(candidate)
            exact_hashes[content_hash] = candidate

        return DeduplicationResult(
            candidates=retained_candidates,
            original_candidate_count=len(candidates),
            duplicate_count=duplicate_count,
        )

    def _find_near_duplicate(
        self,
        candidate: RetrievalCandidate,
        retained_candidates: list[RetrievalCandidate],
    ) -> RetrievalCandidate | None:
        """Find an existing candidate with highly similar content."""

        candidate_tokens = self._tokenize(
            candidate.chunk.text,
        )

        if len(candidate_tokens) < self._minimum_token_count:
            return None

        for retained in retained_candidates:
            retained_tokens = self._tokenize(
                retained.chunk.text,
            )

            if len(retained_tokens) < self._minimum_token_count:
                continue

            similarity = self._jaccard_similarity(
                candidate_tokens,
                retained_tokens,
            )

            if similarity >= self._similarity_threshold:
                return retained

        return None

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for exact duplicate detection."""

        normalized_text = text.casefold()
        normalized_text = re.sub(
            r"\s+",
            " ",
            normalized_text,
        )
        normalized_text = re.sub(
            r"[^\w\s]",
            "",
            normalized_text,
        )

        return normalized_text.strip()

    def _tokenize(
        self,
        text: str,
    ) -> set:
        """Convert normalized content into unique word tokens."""

        return set(self._normalize_text(text).split())

    @staticmethod
    def _calculate_content_hash(
        normalized_text: str,
    ) -> str:
        """Create a stable hash for normalized chunk text."""

        return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()

    @staticmethod
    def _jaccard_similarity(
        first_tokens: set[str],
        second_tokens: set[str],
    ) -> float:
        """Calculate token-set Jaccard similarity."""

        union = first_tokens | second_tokens

        if not union:
            return 0.0

        intersection = first_tokens & second_tokens

        return len(intersection) / len(union)

    @staticmethod
    def _record_duplicate(
        retained: RetrievalCandidate,
        duplicate: RetrievalCandidate,
    ) -> None:
        """Record the removed chunk ID on the retained candidate."""

        if duplicate.chunk.chunk_id not in retained.duplicate_chunk_ids:
            retained.duplicate_chunk_ids.append(duplicate.chunk.chunk_id)
