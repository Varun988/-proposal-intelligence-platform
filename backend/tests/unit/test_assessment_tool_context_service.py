import pytest

from app.core.exceptions import DocumentNotFoundError, ToolPermissionError
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
    assessment_id: str,
    document_id: str,
    chunk_id: str,
    text: str,
    purpose: DocumentPurpose = DocumentPurpose.PROPOSAL,
) -> DocumentChunk:
    """Create one assessment-associated evidence chunk."""

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
            "assessment_id": assessment_id,
            "document_purpose": purpose.value,
        },
    )


def create_services() -> tuple[
    AssessmentToolContextService,
    InMemoryAssessmentVectorIndexRegistry,
    EmbeddingService,
]:
    """Create tool-context dependencies with fake embeddings."""

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
        AssessmentToolContextService(retrieval_context_service=retrieval_context),
        registry,
        embedding_service,
    )


async def index_document(
    registry: InMemoryAssessmentVectorIndexRegistry,
    embedding_service: EmbeddingService,
    assessment_id: str,
    document_id: str,
    chunk_id: str,
    text: str,
    purpose: DocumentPurpose = DocumentPurpose.PROPOSAL,
) -> None:
    """Embed and index one assessment document."""

    chunk = create_chunk(
        assessment_id=assessment_id,
        document_id=document_id,
        chunk_id=chunk_id,
        text=text,
        purpose=purpose,
    )

    result = embedding_service.embed_chunks(
        [chunk],
    )

    await registry.add_document(
        assessment_id=assessment_id,
        document_id=document_id,
        items=result.items,
        embedding_provider=result.provider_name,
        embedding_model=result.model_name,
        vector_dimension=result.dimension,
        document_purpose=purpose,
    )


@pytest.mark.asyncio
async def test_proposal_registry_contains_only_evidence_search() -> None:
    service, registry, embedding_service = create_services()
    await index_document(
        registry=registry,
        embedding_service=embedding_service,
        assessment_id="assessment-001",
        document_id="document-001",
        chunk_id="chunk-001",
        text="Implementation timeline is twelve months.",
    )

    tool_registry = await service.create_proposal_analysis_registry("assessment-001")

    assert tool_registry.registered_names() == ("search_evidence",)
    definitions = tool_registry.definitions_for_agent("proposal-analysis")
    assert len(definitions) == 1
    assert definitions[0].name == "search_evidence"
    assert definitions[0].allowed_agents == ("proposal-analysis",)


@pytest.mark.asyncio
async def test_vendor_registry_is_restricted_to_vendor_agent() -> None:
    service, registry, embedding_service = create_services()
    await index_document(
        registry=registry,
        embedding_service=embedding_service,
        assessment_id="assessment-001",
        document_id="document-001",
        chunk_id="chunk-001",
        text="Vendor profile and financial evidence.",
        purpose=DocumentPurpose.VENDOR_PROFILE,
    )

    tool_registry = await service.create_vendor_research_registry("assessment-001")

    assert tool_registry.definitions_for_agent("proposal-analysis") == ()
    definitions = tool_registry.definitions_for_agent("vendor-research")
    assert len(definitions) == 1
    assert definitions[0].allowed_agents == ("vendor-research",)

    with pytest.raises(ToolPermissionError, match="not permitted"):
        tool_registry.execute(
            tool_name="search_evidence",
            payload={"query": "financial evidence"},
            agent_name="proposal-analysis",
        )


@pytest.mark.asyncio
async def test_registry_searches_only_requested_assessment() -> None:
    service, registry, embedding_service = create_services()
    await index_document(
        registry=registry,
        embedding_service=embedding_service,
        assessment_id="assessment-001",
        document_id="document-001",
        chunk_id="chunk-001",
        text="Implementation timeline is twelve months.",
    )
    await index_document(
        registry=registry,
        embedding_service=embedding_service,
        assessment_id="assessment-002",
        document_id="document-002",
        chunk_id="chunk-002",
        text="Confidential pricing from another assessment.",
    )

    tool_registry = await service.create_proposal_analysis_registry("assessment-001")
    execution = tool_registry.execute(
        tool_name="search_evidence",
        payload={"query": "implementation timeline"},
        agent_name="proposal-analysis",
    )

    candidates = execution.output["response"]["candidates"]
    assert candidates
    assert {candidate["chunk"]["document_id"] for candidate in candidates} == {"document-001"}


@pytest.mark.asyncio
async def test_context_creates_independent_registries() -> None:
    service, registry, embedding_service = create_services()
    await index_document(
        registry=registry,
        embedding_service=embedding_service,
        assessment_id="assessment-001",
        document_id="document-001",
        chunk_id="chunk-001",
        text="Synthetic proposal content.",
    )

    first = await service.create_proposal_analysis_registry("assessment-001")
    second = await service.create_proposal_analysis_registry("assessment-001")

    assert first is not second
    assert first.registered_names() == second.registered_names()


@pytest.mark.asyncio
async def test_context_rejects_unindexed_assessment() -> None:
    service, _, _ = create_services()

    with pytest.raises(DocumentNotFoundError, match="not found"):
        await service.create_proposal_analysis_registry("assessment-missing")
