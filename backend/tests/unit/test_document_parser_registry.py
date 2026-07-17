from pathlib import Path

import pytest

from app.core.exceptions import (
    DocumentParserRegistrationError,
    UnsupportedDocumentError,
)
from app.documents.parsers.pdf import PypdfPDFParser
from app.documents.registry import DocumentParserRegistry


def test_registry_registers_pdf_parser() -> None:
    registry = DocumentParserRegistry()
    parser = PypdfPDFParser()

    registry.register(parser)

    selected_parser = registry.get_parser(
        Path("proposal.pdf"),
    )

    assert selected_parser is parser
    assert registry.supported_extensions() == (".pdf",)


def test_registry_selects_parser_case_insensitively() -> None:
    registry = DocumentParserRegistry()
    parser = PypdfPDFParser()
    registry.register(parser)

    selected_parser = registry.get_parser(
        Path("PROPOSAL.PDF"),
    )

    assert selected_parser is parser


def test_registry_rejects_duplicate_extension() -> None:
    registry = DocumentParserRegistry()
    registry.register(PypdfPDFParser())

    with pytest.raises(
        DocumentParserRegistrationError,
        match="already registered",
    ):
        registry.register(PypdfPDFParser())


def test_registry_rejects_unsupported_extension() -> None:
    registry = DocumentParserRegistry()
    registry.register(PypdfPDFParser())

    with pytest.raises(
        UnsupportedDocumentError,
        match="No document parser is registered",
    ):
        registry.get_parser(
            Path("proposal.docx"),
        )


def test_empty_registry_has_no_supported_extensions() -> None:
    registry = DocumentParserRegistry()

    assert registry.supported_extensions() == ()
