from app.rag.deduplication.content import ContentDeduplicator
from app.rag.reranking.lexical import LexicalRetrievalReranker
from app.rag.vector_store.faiss_store import FaissVectorStore
from app.schemas.chunk import (
    ChunkCitation,
    DocumentChunk,
)
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from app.tools.indexing_tools import IndexDocumentTool
from app.tools.registry import ToolRegistry
from app.tools.retrieval_tools import SearchEvidenceTool
from tests.embedding_fakes import FakeEmbeddingProvider


def create_chunk(
    chunk_id: str,
    text: str,
    page_number: int,
    document_chunk_index: int,
) -> DocumentChunk:
    """Create a synthetic evidence chunk for tool tests."""

    return DocumentChunk(
        chunk_id=chunk_id,
        document_id="document-001",
        text=text,
        page_number=page_number,
        page_chunk_index=0,
        document_chunk_index=document_chunk_index,
        citation=ChunkCitation(
            document_id="document-001",
            file_name="synthetic-proposal.pdf",
            page_number=page_number,
            checksum_sha256="a" * 64,
        ),
        metadata={
            "data_classification": "synthetic",
        },
    )


def create_components() -> tuple[
    IndexDocumentTool,
    SearchEvidenceTool,
    FaissVectorStore,
]:
    """Create indexing and retrieval tools sharing one vector store."""

    embedding_service = EmbeddingService(
        provider=FakeEmbeddingProvider(
            dimension=3,
        )
    )

    vector_store = FaissVectorStore(
        dimension=3,
    )

    retrieval_service = RetrievalService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        deduplicator=ContentDeduplicator(),
        reranker=LexicalRetrievalReranker(
            retrieval_weight=0.2,
            lexical_weight=0.8,
        ),
        candidate_limit=3,
        final_limit=2,
    )

    index_tool = IndexDocumentTool(
        embedding_service=embedding_service,
        vector_store=vector_store,
    )

    search_tool = SearchEvidenceTool(
        retrieval_service=retrieval_service,
    )

    return index_tool, search_tool, vector_store


def create_chunks() -> list:
    """Create synthetic evidence including one exact duplicate."""

    return [
        create_chunk(
            chunk_id="delivery-primary",
            text=("The proposed project delivery timeline is twelve months."),
            page_number=1,
            document_chunk_index=0,
        ),
        create_chunk(
            chunk_id="delivery-duplicate",
            text=("The proposed project delivery timeline is twelve months."),
            page_number=2,
            document_chunk_index=1,
        ),
        create_chunk(
            chunk_id="security",
            text=("Customer information is encrypted at rest and in transit."),
            page_number=3,
            document_chunk_index=2,
        ),
    ]


def test_index_document_tool_indexes_chunks() -> None:
    index_tool, _, vector_store = create_components()
    chunks = create_chunks()

    result = index_tool.run(
        payload={
            "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
        }
    )

    assert result.succeeded
    assert result.output is not None
    assert result.output["indexed_chunk_count"] == 3
    assert result.output["vector_store_size"] == 3
    assert result.output["vector_dimension"] == 3
    assert result.output["embedding_provider"] == ("fake-embeddings")
    assert result.output["embedding_model"] == ("fake-embedding-model")
    assert vector_store.size == 3


def test_search_evidence_tool_executes_full_pipeline() -> None:
    index_tool, search_tool, _ = create_components()

    index_tool.run(
        payload={
            "chunks": [chunk.model_dump(mode="json") for chunk in create_chunks()],
        }
    )

    result = search_tool.run(
        payload={
            "query": "What is the project delivery timeline?",
        },
        metadata={
            "assessment_id": "assessment-001",
        },
    )

    assert result.succeeded
    assert result.output is not None

    response = result.output["response"]

    assert response["query"] == ("What is the project delivery timeline?")
    assert response["metrics"]["initial_candidate_count"] == 3
    assert response["metrics"]["duplicate_count"] == 1
    assert response["metrics"]["final_result_count"] == 2

    top_candidate = response["candidates"][0]

    assert "delivery timeline" in (top_candidate["chunk"]["text"].casefold())
    assert top_candidate["citation_label"] in {
        "synthetic-proposal.pdf, page 1",
        "synthetic-proposal.pdf, page 2",
    }
    assert top_candidate["final_score"] is not None


def test_search_tool_preserves_duplicate_traceability() -> None:
    index_tool, search_tool, _ = create_components()

    index_tool.run(
        payload={
            "chunks": [chunk.model_dump(mode="json") for chunk in create_chunks()],
        }
    )

    result = search_tool.run(
        payload={
            "query": "project delivery timeline",
        }
    )

    assert result.output is not None

    response = result.output["response"]
    delivery_candidate = response["candidates"][0]

    assert delivery_candidate["duplicate_count"] == 1
    assert len(delivery_candidate["duplicate_chunk_ids"]) == 1


def test_tool_registry_executes_index_and_search_tools() -> None:
    index_tool, search_tool, _ = create_components()

    registry = ToolRegistry()
    registry.register(index_tool)
    registry.register(search_tool)

    index_result = registry.execute(
        tool_name="index_document",
        payload={
            "chunks": [chunk.model_dump(mode="json") for chunk in create_chunks()],
        },
        agent_name="proposal-analysis",
    )

    assert index_result.succeeded

    search_result = registry.execute(
        tool_name="search_evidence",
        payload={
            "query": "project delivery timeline",
        },
        agent_name="proposal-analysis",
    )

    assert search_result.succeeded
    assert search_result.metadata["agent_name"] == ("proposal-analysis")


def test_tools_expose_expected_permissions() -> None:
    index_tool, search_tool, _ = create_components()

    assert index_tool.allowed_agents == (
        "orchestrator",
        "proposal-analysis",
    )

    assert search_tool.allowed_agents == (
        "orchestrator",
        "proposal-analysis",
        "risk-report",
        "vendor-research",
    )
