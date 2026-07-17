import pytest

from app.core.exceptions import (
    DocumentConflictError,
    DocumentNotFoundError,
)
from app.rag.vector_store.faiss_store import (
    FaissVectorStore,
)
from app.repositories.assessment_vector_index import (
    InMemoryAssessmentVectorIndexRegistry,
)
from app.schemas.chunk import (
    ChunkCitation,
    DocumentChunk,
)
from app.schemas.embedding import (
    EmbeddedChunk,
    EmbeddingVector,
)


def create_item(
    document_id: str,
    chunk_id: str,
) -> EmbeddedChunk:
    """Create one synthetic embedded chunk."""

    chunk = DocumentChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        text="Synthetic content.",
        page_number=1,
        page_chunk_index=0,
        document_chunk_index=0,
        citation=ChunkCitation(
            document_id=document_id,
            file_name="synthetic.txt",
            page_number=1,
            checksum_sha256="a" * 64,
        ),
        metadata={
            "assessment_id": "assessment-001",
            "document_purpose": "proposal",
        },
    )

    return EmbeddedChunk(
        chunk=chunk,
        embedding=EmbeddingVector(
            values=[
                1.0,
                0.0,
                0.0,
            ],
        ),
        model_name="fake-model",
        provider_name="fake-provider",
    )


def create_registry() -> InMemoryAssessmentVectorIndexRegistry:
    """Create a FAISS registry for tests."""

    return InMemoryAssessmentVectorIndexRegistry(
        vector_store_factory=lambda dimension: FaissVectorStore(
            dimension=dimension,
        )
    )


@pytest.mark.asyncio
async def test_registry_creates_assessment_index() -> None:
    registry = create_registry()

    metadata = await registry.add_document(
        assessment_id="assessment-001",
        document_id="document-001",
        items=[
            create_item(
                document_id="document-001",
                chunk_id="chunk-001",
            )
        ],
        embedding_provider="fake-provider",
        embedding_model="fake-model",
        vector_dimension=3,
    )

    assert metadata.assessment_id == "assessment-001"
    assert metadata.document_ids == [
        "document-001",
    ]
    assert metadata.vector_store_size == 1


@pytest.mark.asyncio
async def test_registry_isolates_assessments() -> None:
    registry = create_registry()

    await registry.add_document(
        assessment_id="assessment-001",
        document_id="document-001",
        items=[
            create_item(
                document_id="document-001",
                chunk_id="chunk-001",
            )
        ],
        embedding_provider="fake-provider",
        embedding_model="fake-model",
        vector_dimension=3,
    )

    assert (
        await registry.contains_document(
            "assessment-001",
            "document-001",
        )
        is True
    )

    assert (
        await registry.contains_document(
            "assessment-002",
            "document-001",
        )
        is False
    )

    with pytest.raises(
        DocumentNotFoundError,
        match="not found",
    ):
        await registry.get_store(
            "assessment-002",
        )


@pytest.mark.asyncio
async def test_registry_rejects_duplicate_document() -> None:
    registry = create_registry()

    items = [
        create_item(
            document_id="document-001",
            chunk_id="chunk-001",
        )
    ]

    await registry.add_document(
        assessment_id="assessment-001",
        document_id="document-001",
        items=items,
        embedding_provider="fake-provider",
        embedding_model="fake-model",
        vector_dimension=3,
    )

    with pytest.raises(
        DocumentConflictError,
        match="already indexed",
    ):
        await registry.add_document(
            assessment_id="assessment-001",
            document_id="document-001",
            items=items,
            embedding_provider="fake-provider",
            embedding_model="fake-model",
            vector_dimension=3,
        )

@pytest.mark.asyncio
async def test_registry_rejects_missing_document_purpose(
) -> None:
    registry = create_registry()

    item = create_item(
        document_id="document-001",
        chunk_id="chunk-001",
    )

    item.chunk.metadata.pop(
        "document_purpose",
    )

    with pytest.raises(
        ValueError,
        match="require document-purpose metadata",
    ):
        await registry.add_document(
            assessment_id="assessment-001",
            document_id="document-001",
            items=[item],
            embedding_provider="fake-provider",
            embedding_model="fake-model",
            vector_dimension=3,
        )