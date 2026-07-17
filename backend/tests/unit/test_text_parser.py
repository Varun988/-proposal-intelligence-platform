from pathlib import Path

import pytest

from app.core.exceptions import DocumentExtractionError
from app.documents.parsers.text import Utf8TextDocumentParser
from app.schemas.document import DocumentType


def test_text_parser_extracts_single_page(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "proposal.txt"

    file_path.write_text(
        "Synthetic proposal content.",
        encoding="utf-8",
    )

    result = Utf8TextDocumentParser().parse(
        file_path,
    )

    assert result.document_type is DocumentType.TEXT
    assert result.mime_type == "text/plain"
    assert result.page_count == 1
    assert result.pages[0].text == "Synthetic proposal content."
    assert result.extracted_character_count == 27
    assert len(result.checksum_sha256) == 64


def test_text_parser_rejects_non_utf8(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "proposal.txt"

    invalid_utf8 = bytes(
        [
            0xFF,
            0xFE,
            0x00,
        ]
    )

    file_path.write_bytes(
        invalid_utf8,
    )

    with pytest.raises(
        DocumentExtractionError,
        match="must use UTF-8",
    ):
        Utf8TextDocumentParser().parse(
            file_path,
        )
