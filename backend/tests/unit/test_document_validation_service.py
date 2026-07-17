import pytest

from app.core.exceptions import DocumentValidationError
from app.schemas.document_upload import (
    DocumentMediaType,
)
from app.services.document_validation_service import (
    DocumentValidationService,
)


def test_validation_accepts_pdf() -> None:
    service = DocumentValidationService()

    result = service.validate(
        original_file_name="proposal.pdf",
        declared_media_type="application/pdf",
        content=b"%PDF-1.7 synthetic",
    )

    assert result is DocumentMediaType.PDF


def test_validation_accepts_utf8_text() -> None:
    service = DocumentValidationService()

    result = service.validate(
        original_file_name="proposal.txt",
        declared_media_type="text/plain",
        content=b"Synthetic proposal content.",
    )

    assert result is DocumentMediaType.TEXT


def test_validation_rejects_empty_content() -> None:
    service = DocumentValidationService()

    with pytest.raises(
        DocumentValidationError,
        match="cannot be empty",
    ):
        service.validate(
            original_file_name="proposal.pdf",
            declared_media_type="application/pdf",
            content=b"",
        )


def test_validation_rejects_invalid_pdf_signature() -> None:
    service = DocumentValidationService()

    with pytest.raises(
        DocumentValidationError,
        match="invalid file signature",
    ):
        service.validate(
            original_file_name="proposal.pdf",
            declared_media_type="application/pdf",
            content=b"not-a-pdf",
        )


def test_validation_rejects_mismatched_media_type() -> None:
    service = DocumentValidationService()

    with pytest.raises(
        DocumentValidationError,
        match="does not match",
    ):
        service.validate(
            original_file_name="proposal.pdf",
            declared_media_type="text/plain",
            content=b"%PDF-1.7 synthetic",
        )


def test_validation_rejects_oversized_file() -> None:
    service = DocumentValidationService(
        maximum_file_size_bytes=5,
    )

    with pytest.raises(
        DocumentValidationError,
        match="exceeds",
    ):
        service.validate(
            original_file_name="proposal.txt",
            declared_media_type="text/plain",
            content=b"too large",
        )
