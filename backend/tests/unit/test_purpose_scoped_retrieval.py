import pytest

from app.rag.vector_store.faiss_store import FaissVectorStore
from app.repositories.assessment_vector_index import (
    InMemoryAssessmentVectorIndexRegistry,
)
from app.schemas.chunk import ChunkCitation, DocumentChunk
from app.schemas.document_upload import DocumentPurpose
from app.services.assessment_retrieval_context_service import (
    AssessmentRetrievalContextService,
)
from app.services.assessment_tool_context_service import (
    AssessmentToolContextService,
)
from app.services.embedding_service import EmbeddingService
from tests.embedding_fakes import FakeEmbeddingProvider


def create_chunk(
    document_id: str,
    chunk_id: str,
    purpose: DocumentPurpose,
    text: str,
) -> DocumentChunk:
    """Create one purpose-labelled chunk."""

    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        text=text,
        page_number=1,
        page_chunk_index=0,
        document_chunk_index=0,
        citation=ChunkCitation(
            document_id=document_id,
            file_name=f"{document_id}.txt",
            page_number=1,
            checksum_sha256="a" * 64,
        ),
        metadata={
            "assessment_id": "assessment-001",
            "document_purpose": purpose.value,
        },
    )


async def add_document(
    registry: InMemoryAssessmentVectorIndexRegistry,
    embedding_service: EmbeddingService,
    document_id: str,
    chunk_id: str,
    purpose: DocumentPurpose,
    text: str,
) -> None:
    """Embed and purpose-index one document."""

    chunk = create_chunk(document_id, chunk_id, purpose, text)
    result = embedding_service.embed_chunks([chunk])
    await registry.add_document(
        assessment_id="assessment-001",
        document_id=document_id,
        items=result.items,
        embedding_provider=result.provider_name,
        embedding_model=result.model_name,
        vector_dimension=result.dimension,
        document_purpose=purpose,
    )


async def create_context() -> tuple[
    AssessmentToolContextService,
    InMemoryAssessmentVectorIndexRegistry,
    EmbeddingService,
]:
    """Create a purpose-scoped tool context."""

    embedding_service = EmbeddingService(provider=FakeEmbeddingProvider(dimension=3))
    registry = InMemoryAssessmentVectorIndexRegistry(
        vector_store_factory=lambda dimension: FaissVectorStore(dimension=dimension)
    )
    retrieval_context = AssessmentRetrievalContextService(
        embedding_service=embedding_service,
        index_registry=registry,
        candidate_limit=10,
        final_limit=5,
    )
    return (
        AssessmentToolContextService(retrieval_context),
        registry,
        embedding_service,
    )


@pytest.mark.asyncio
async def test_proposal_tool_cannot_retrieve_vendor_profile() -> None:
    service, registry, embeddings = await create_context()
    await add_document(
        registry,
        embeddings,
        "proposal-001",
        "proposal-chunk",
        DocumentPurpose.PROPOSAL,
        "Implementation timeline is twelve months.",
    )
    await add_document(
        registry,
        embeddings,
        "vendor-001",
        "vendor-chunk",
        DocumentPurpose.VENDOR_PROFILE,
        "Vendor financial profile and certification claims.",
    )

    tools = await service.create_proposal_analysis_registry("assessment-001")
    result = tools.execute(
        "search_evidence",
        {"query": "timeline financial certification"},
        "proposal-analysis",
    )
    candidates = result.output["response"]["candidates"]

    assert candidates
    assert {candidate["chunk"]["document_id"] for candidate in candidates} == {"proposal-001"}


@pytest.mark.asyncio
async def test_vendor_tool_cannot_retrieve_proposal() -> None:
    service, registry, embeddings = await create_context()
    await add_document(
        registry,
        embeddings,
        "proposal-001",
        "proposal-chunk",
        DocumentPurpose.PROPOSAL,
        "Implementation timeline is twelve months.",
    )
    await add_document(
        registry,
        embeddings,
        "vendor-001",
        "vendor-chunk",
        DocumentPurpose.VENDOR_PROFILE,
        "Vendor financial profile and certification claims.",
    )

    tools = await service.create_vendor_research_registry("assessment-001")
    result = tools.execute(
        "search_evidence",
        {"query": "timeline financial certification"},
        "vendor-research",
    )
    candidates = result.output["response"]["candidates"]

    assert candidates
    assert {candidate["chunk"]["document_id"] for candidate in candidates} == {"vendor-001"}


@pytest.mark.asyncio
async def test_supporting_evidence_is_available_to_both_specialists() -> None:
    service, registry, embeddings = await create_context()
    await add_document(
        registry,
        embeddings,
        "support-001",
        "support-chunk",
        DocumentPurpose.SUPPORTING_EVIDENCE,
        "Approved supporting evidence for the assessment.",
    )

    proposal_tools = await service.create_proposal_analysis_registry("assessment-001")
    vendor_tools = await service.create_vendor_research_registry("assessment-001")

    proposal_result = proposal_tools.execute(
        "search_evidence",
        {"query": "approved supporting evidence"},
        "proposal-analysis",
    )
    vendor_result = vendor_tools.execute(
        "search_evidence",
        {"query": "approved supporting evidence"},
        "vendor-research",
    )

    assert proposal_result.output["response"]["candidates"]
    assert vendor_result.output["response"]["candidates"]
