from pathlib import Path

import pytest

from app.core.exceptions import (
    DocumentNotFoundError,
    UnsupportedDocumentError,
)
from app.documents.parsers.pdf import PypdfPDFParser
from app.schemas.document import DocumentType
from tests.fixtures.pdf_factory import create_test_pdf


def test_parser_supports_pdf_extension() -> None:
    parser = PypdfPDFParser()

    assert parser.supported_extensions == (".pdf",)
    assert parser.can_parse(Path("proposal.pdf"))
    assert parser.can_parse(Path("PROPOSAL.PDF"))
    assert not parser.can_parse(Path("proposal.docx"))


def test_parser_extracts_pages_and_metadata(
    tmp_path: Path,
) -> None:
    pdf_path = create_test_pdf(
        file_path=tmp_path / "proposal.pdf",
        pages=[
            "Project duration is twelve months.",
            "The proposal includes twenty consultants.",
        ],
    )
    parser = PypdfPDFParser()

    document = parser.parse(pdf_path)

    assert document.file_name == "proposal.pdf"
    assert document.document_type is DocumentType.PDF
    assert document.mime_type == "application/pdf"
    assert document.page_count == 2
    assert len(document.pages) == 2

    assert document.pages[0].page_number == 1
    assert (
        "Project duration is twelve months."
        in document.pages[0].text
    )

    assert document.pages[1].page_number == 2
    assert (
        "The proposal includes twenty consultants."
        in document.pages[1].text
    )

    assert document.metadata.title == "Synthetic Proposal"
    assert (
        document.metadata.author
        == "Proposal Intelligence Tests"
    )

    assert document.text_page_count == 2
    assert document.extracted_character_count > 0
    assert len(document.checksum_sha256) == 64


def test_parser_preserves_page_boundaries(
    tmp_path: Path,
) -> None:
    pdf_path = create_test_pdf(
        file_path=tmp_path / "proposal.pdf",
        pages=[
            "First page content.",
            "Second page content.",
        ],
    )
    parser = PypdfPDFParser()

    document = parser.parse(pdf_path)

    assert document.pages[0].text == "First page content."
    assert document.pages[1].text == "Second page content."
    assert document.full_text == (
        "First page content.\n\nSecond page content."
    )


def test_parser_generates_stable_checksum(
    tmp_path: Path,
) -> None:
    pdf_path = create_test_pdf(
        file_path=tmp_path / "proposal.pdf",
        pages=["Synthetic proposal content."],
    )
    parser = PypdfPDFParser()

    first_result = parser.parse(pdf_path)
    second_result = parser.parse(pdf_path)

    assert (
        first_result.checksum_sha256
        == second_result.checksum_sha256
    )
    assert first_result.document_id != second_result.document_id


def test_parser_rejects_missing_file(
    tmp_path: Path,
) -> None:
    parser = PypdfPDFParser()

    with pytest.raises(
        DocumentNotFoundError,
        match="Document not found",
    ):
        parser.parse(tmp_path / "missing.pdf")


def test_parser_rejects_unsupported_extension(
    tmp_path: Path,
) -> None:
    text_path = tmp_path / "proposal.txt"
    text_path.write_text(
        "Synthetic proposal content.",
        encoding="utf-8",
    )
    parser = PypdfPDFParser()

    with pytest.raises(
        UnsupportedDocumentError,
        match="Unsupported document type",
    ):
        parser.parse(text_path)
