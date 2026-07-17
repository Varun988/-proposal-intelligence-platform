import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_document_repository,
    get_document_service,
    get_document_storage,
    get_document_validation_service,
)
from app.main import app


@pytest.fixture(autouse=True)
def reset_document_dependencies():
    """Reset document dependencies between tests."""

    get_document_service.cache_clear()
    get_document_validation_service.cache_clear()
    get_document_storage.cache_clear()
    get_document_repository.cache_clear()

    app.dependency_overrides.clear()

    yield

    app.dependency_overrides.clear()

    get_document_service.cache_clear()
    get_document_validation_service.cache_clear()
    get_document_storage.cache_clear()
    get_document_repository.cache_clear()


@pytest.fixture
def client() -> TestClient:
    """Create an isolated API test client."""

    return TestClient(app)


def test_upload_text_document(
    client: TestClient,
) -> None:
    content = b"Synthetic proposal content."

    response = client.post(
        "/api/v1/documents",
        data={
            "purpose": "proposal",
            "is_public_source": "false",
        },
        files={
            "file": (
                "proposal.txt",
                content,
                "text/plain",
            ),
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["document_id"].startswith("document-")
    assert response_data["original_file_name"] == "proposal.txt"
    assert response_data["media_type"] == "text/plain"
    assert response_data["purpose"] == "proposal"
    assert response_data["lifecycle_status"] == "stored"
    assert response_data["file_size_bytes"] == len(content)

    assert len(response_data["checksum_sha256"]) == 64


def test_upload_pdf_document(
    client: TestClient,
) -> None:
    content = b"%PDF-1.7 synthetic proposal"

    response = client.post(
        "/api/v1/documents",
        data={
            "purpose": "rfp",
        },
        files={
            "file": (
                "requirements.pdf",
                content,
                "application/pdf",
            ),
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["media_type"] == ("application/pdf")
    assert response_data["purpose"] == "rfp"


def test_upload_vendor_profile_requires_vendor_name(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/documents",
        data={
            "purpose": "vendor_profile",
        },
        files={
            "file": (
                "vendor.txt",
                b"Synthetic vendor profile.",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 422

    detail = response.json()["detail"]

    assert detail["error_code"] == ("document_metadata_invalid")


def test_upload_vendor_profile_accepts_vendor_name(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/documents",
        data={
            "purpose": "vendor_profile",
            "vendor_name": "Example Digital Services",
            "source_name": "Synthetic Vendor Profile",
            "is_public_source": "false",
        },
        files={
            "file": (
                "vendor.txt",
                b"Synthetic vendor profile.",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 201
    assert response.json()["purpose"] == ("vendor_profile")


def test_get_document_status(
    client: TestClient,
) -> None:
    upload_response = client.post(
        "/api/v1/documents",
        data={
            "purpose": "proposal",
        },
        files={
            "file": (
                "proposal.txt",
                b"Synthetic proposal content.",
                "text/plain",
            ),
        },
    )

    assert upload_response.status_code == 201

    document_id = upload_response.json()["document_id"]

    status_response = client.get(
        f"/api/v1/documents/{document_id}",
    )

    assert status_response.status_code == 200

    status_data = status_response.json()

    assert status_data["document_id"] == document_id
    assert status_data["purpose"] == "proposal"
    assert status_data["lifecycle_status"] == "stored"
    assert status_data["page_count"] is None
    assert status_data["extracted_character_count"] == 0
    assert status_data["chunk_count"] == 0


def test_get_unknown_document_returns_not_found(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/documents/document-missing",
    )

    assert response.status_code == 404

    detail = response.json()["detail"]

    assert detail["error_code"] == "document_not_found"
    assert detail["document_id"] == "document-missing"


def test_upload_rejects_invalid_pdf_signature(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/documents",
        data={
            "purpose": "proposal",
        },
        files={
            "file": (
                "proposal.pdf",
                b"This is not a PDF.",
                "application/pdf",
            ),
        },
    )

    assert response.status_code == 422

    detail = response.json()["detail"]

    assert detail["error_code"] == ("document_validation_failed")

    assert "invalid file signature" in (detail["message"])


def test_upload_rejects_media_type_mismatch(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/documents",
        data={
            "purpose": "proposal",
        },
        files={
            "file": (
                "proposal.txt",
                b"Synthetic proposal content.",
                "application/pdf",
            ),
        },
    )

    assert response.status_code == 422

    detail = response.json()["detail"]

    assert detail["error_code"] == ("document_validation_failed")

    assert "does not match" in detail["message"]


def test_upload_rejects_unsupported_extension(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/documents",
        data={
            "purpose": "proposal",
        },
        files={
            "file": (
                "proposal.docx",
                b"Synthetic content.",
                ("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ),
        },
    )

    assert response.status_code == 422

    detail = response.json()["detail"]

    assert detail["error_code"] == ("document_validation_failed")
