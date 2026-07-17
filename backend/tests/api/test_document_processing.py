import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_assessment_vector_index_registry,
    get_document_chunk_processing_service,
    get_document_chunk_repository,
    get_document_chunking_service,
    get_document_extraction_service,
    get_document_indexing_service,
    get_document_parser_registry,
    get_document_pipeline_service,
    get_document_processing_service,
    get_document_repository,
    get_document_service,
    get_document_storage,
    get_document_validation_service,
    get_embedding_service,
    get_extracted_document_repository,
)
from app.main import app
from app.rag.chunking import PageAwareDocumentChunker
from app.rag.vector_store.faiss_store import FaissVectorStore
from app.repositories.assessment_vector_index import (
    InMemoryAssessmentVectorIndexRegistry,
)
from app.services.document_chunk_processing_service import (
    DocumentChunkProcessingService,
)
from app.services.document_chunking_service import (
    DocumentChunkingService,
)
from app.services.document_indexing_service import (
    DocumentIndexingService,
)
from app.services.document_pipeline_service import (
    DocumentPipelineService,
)
from app.services.embedding_service import EmbeddingService
from tests.embedding_fakes import FakeEmbeddingProvider

DOCUMENT_DEPENDENCIES = [
    get_document_pipeline_service,
    get_document_indexing_service,
    get_assessment_vector_index_registry,
    get_embedding_service,
    get_document_chunk_processing_service,
    get_document_chunking_service,
    get_document_chunk_repository,
    get_document_processing_service,
    get_document_extraction_service,
    get_document_parser_registry,
    get_extracted_document_repository,
    get_document_service,
    get_document_validation_service,
    get_document_storage,
    get_document_repository,
]


@pytest.fixture
def fake_pipeline_service() -> DocumentPipelineService:
    """Create a pipeline using deterministic fake embeddings."""

    embedding_service = EmbeddingService(
        provider=FakeEmbeddingProvider(
            dimension=3,
        )
    )

    index_registry = InMemoryAssessmentVectorIndexRegistry(
        vector_store_factory=lambda dimension: FaissVectorStore(
            dimension=dimension,
        )
    )

    chunk_processing_service = DocumentChunkProcessingService(
        document_repository=(get_document_repository()),
        extracted_document_repository=(get_extracted_document_repository()),
        chunk_repository=(get_document_chunk_repository()),
        chunking_service=DocumentChunkingService(
            chunker=PageAwareDocumentChunker(
                max_characters=1_500,
                overlap_characters=200,
            )
        ),
    )

    indexing_service = DocumentIndexingService(
        document_repository=get_document_repository(),
        chunk_repository=get_document_chunk_repository(),
        index_registry=index_registry,
        embedding_service=embedding_service,
    )

    return DocumentPipelineService(
        extraction_service=(get_document_processing_service()),
        chunk_processing_service=(chunk_processing_service),
        indexing_service=indexing_service,
    )


@pytest.fixture(autouse=True)
def reset_document_dependencies():
    """Reset cached document dependencies between tests."""

    for dependency in DOCUMENT_DEPENDENCIES:
        dependency.cache_clear()

    app.dependency_overrides.clear()

    yield

    app.dependency_overrides.clear()

    for dependency in DOCUMENT_DEPENDENCIES:
        dependency.cache_clear()


@pytest.fixture
def client(
    fake_pipeline_service: DocumentPipelineService,
) -> TestClient:
    """Create a client using deterministic fake embeddings."""

    app.dependency_overrides[get_document_pipeline_service] = lambda: fake_pipeline_service

    return TestClient(app)


def upload_text_document(
    client: TestClient,
) -> str:
    """Upload a synthetic text document."""

    response = client.post(
        "/api/v1/documents",
        data={
            "purpose": "proposal",
            "assessment_id": "assessment-001",
        },
        files={
            "file": (
                "proposal.txt",
                b"Synthetic proposal content.",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 201

    return response.json()["document_id"]


def test_process_document_returns_accepted(
    client: TestClient,
) -> None:
    document_id = upload_text_document(client)

    response = client.post(
        f"/api/v1/documents/{document_id}/process",
    )

    assert response.status_code == 202

    response_data = response.json()

    assert response_data["document_id"] == document_id
    assert response_data["processing_accepted"] is True
    assert response_data["lifecycle_status"] == "extraction_pending"


def test_background_processing_persists_chunks(
    client: TestClient,
) -> None:
    document_id = upload_text_document(client)

    response = client.post(
        f"/api/v1/documents/{document_id}/process",
    )

    assert response.status_code == 202

    status_response = client.get(
        f"/api/v1/documents/{document_id}",
    )

    assert status_response.status_code == 200

    status_data = status_response.json()

    assert status_data["lifecycle_status"] == "indexed"
    assert status_data["chunk_count"] == 1
    assert status_data["page_count"] == 1
    assert status_data["extracted_character_count"] == 27
    assert status_data["error_message"] is None


def test_process_unknown_document_returns_not_found(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/documents/document-missing/process",
    )

    assert response.status_code == 404

    detail = response.json()["detail"]

    assert detail["error_code"] == "document_not_found"


def test_duplicate_processing_returns_conflict(
    client: TestClient,
) -> None:
    document_id = upload_text_document(client)

    first_response = client.post(
        f"/api/v1/documents/{document_id}/process",
    )

    assert first_response.status_code == 202

    second_response = client.post(
        f"/api/v1/documents/{document_id}/process",
    )

    assert second_response.status_code == 409

    detail = second_response.json()["detail"]

    assert detail["error_code"] == "document_processing_conflict"
