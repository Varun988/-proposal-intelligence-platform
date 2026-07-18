from collections.abc import Iterable

from app.rag.deduplication.content import ContentDeduplicator
from app.rag.reranking.lexical import LexicalRetrievalReranker
from app.repositories.assessment_vector_index import (
    AssessmentVectorIndexRegistryProtocol,
)
from app.schemas.document_upload import DocumentPurpose
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService


class AssessmentRetrievalContextService:
    """Create isolated assessment and purpose-scoped retrieval pipelines."""

    PROPOSAL_PURPOSES = (
        DocumentPurpose.PROPOSAL,
        DocumentPurpose.RFP,
        DocumentPurpose.SUPPORTING_EVIDENCE,
    )
    VENDOR_PURPOSES = (
        DocumentPurpose.VENDOR_PROFILE,
        DocumentPurpose.SUPPORTING_EVIDENCE,
    )

    def __init__(
        self,
        embedding_service: EmbeddingService,
        index_registry: AssessmentVectorIndexRegistryProtocol,
        candidate_limit: int = 20,
        final_limit: int = 5,
        deduplication_similarity_threshold: float = 0.9,
        retrieval_weight: float = 0.7,
        lexical_weight: float = 0.3,
    ) -> None:
        if candidate_limit < 1:
            raise ValueError("Candidate limit must be at least one.")
        if final_limit < 1:
            raise ValueError("Final limit must be at least one.")
        if final_limit > candidate_limit:
            raise ValueError("Final limit cannot be greater than candidate limit.")

        self._embedding_service = embedding_service
        self._index_registry = index_registry
        self._candidate_limit = candidate_limit
        self._final_limit = final_limit
        self._deduplication_similarity_threshold = deduplication_similarity_threshold
        self._retrieval_weight = retrieval_weight
        self._lexical_weight = lexical_weight

    async def create_retrieval_service(
        self,
        assessment_id: str,
    ) -> RetrievalService:
        """Create a backward-compatible full assessment retrieval service."""

        return await self._create_service(
            assessment_id=assessment_id,
            purposes=None,
        )

    async def create_proposal_retrieval_service(
        self,
        assessment_id: str,
    ) -> RetrievalService:
        """Create retrieval for proposal, RFP, and supporting evidence."""

        return await self._create_service(
            assessment_id=assessment_id,
            purposes=self.PROPOSAL_PURPOSES,
        )

    async def create_vendor_retrieval_service(
        self,
        assessment_id: str,
    ) -> RetrievalService:
        """Create retrieval for vendor and supporting evidence."""

        return await self._create_service(
            assessment_id=assessment_id,
            purposes=self.VENDOR_PURPOSES,
        )

    async def _create_service(
        self,
        assessment_id: str,
        purposes: Iterable[DocumentPurpose] | None,
    ) -> RetrievalService:
        """Create one explicit scoped retrieval pipeline."""

        normalized_assessment_id = assessment_id.strip()
        if not normalized_assessment_id:
            raise ValueError("Assessment ID is required for retrieval.")

        vector_store = await self._index_registry.get_store(
            normalized_assessment_id,
            purposes=purposes,
        )
        if vector_store.dimension != self._embedding_service.dimension:
            raise ValueError(
                "Assessment index dimension does not match the configured embedding dimension."
            )

        return RetrievalService(
            embedding_service=self._embedding_service,
            vector_store=vector_store,
            deduplicator=ContentDeduplicator(
                similarity_threshold=(self._deduplication_similarity_threshold)
            ),
            reranker=LexicalRetrievalReranker(
                retrieval_weight=self._retrieval_weight,
                lexical_weight=self._lexical_weight,
            ),
            candidate_limit=self._candidate_limit,
            final_limit=self._final_limit,
        )
