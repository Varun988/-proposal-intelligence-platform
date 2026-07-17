from pathlib import Path

import pytest

from app.core.exceptions import UnsupportedDocumentError
from app.documents.parsers.pdf import PypdfPDFParser
from app.documents.registry import DocumentParserRegistry
from app.services.document_extraction_service import (
    DocumentExtractionService,
)
from tests.fixtures.pdf_factory import create_test_pdf


def create_service() -> DocumentExtractionService:
    """Create an extraction service configured for PDF files."""

    registry = DocumentParserRegistry()
    registry.register(PypdfPDFParser())

    return DocumentExtractionService(
        registry=registry,
    )


def test_service_extracts_registered_pdf(
    tmp_path: Path,
) -> None:
    pdf_path = create_test_pdf(
        file_path=tmp_path / "proposal.pdf",
        pages=[
            "The implementation duration is twelve months.",
            "The support period is three years.",
        ],
    )
    service = create_service()

    document = service.extract(pdf_path)

    assert document.file_name == "proposal.pdf"
    assert document.page_count == 2
    assert document.pages[0].page_number == 1
    assert document.pages[1].page_number == 2
    assert "twelve months" in document.pages[0].text
    assert "three years" in document.pages[1].text


def test_service_accepts_string_path(
    tmp_path: Path,
) -> None:
    pdf_path = create_test_pdf(
        file_path=tmp_path / "proposal.pdf",
        pages=["Synthetic proposal content."],
    )
    service = create_service()

    document = service.extract(
        str(pdf_path),
    )

    assert document.file_name == "proposal.pdf"
    assert document.page_count == 1


def test_service_reports_supported_extensions() -> None:
    service = create_service()

    assert service.supported_extensions() == (".pdf",)
    assert service.supports("proposal.pdf")
    assert service.supports("PROPOSAL.PDF")
    assert not service.supports("proposal.docx")


def test_service_rejects_unregistered_document_type() -> None:
    service = create_service()

    with pytest.raises(
        UnsupportedDocumentError,
        match="No document parser is registered",
    ):
        service.extract("proposal.docx")
