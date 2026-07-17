from pathlib import Path

import pytest

from app.core.exceptions import (
    InvalidChunkingConfigurationError,
)
from app.rag.chunking import PageAwareDocumentChunker
from app.schemas.document import (
    DocumentMetadata,
    DocumentPage,
    DocumentType,
    ExtractedDocument,
)
from app.services.document_chunking_service import (
    DocumentChunkingService,
)


def create_document(
    pages: list[str],
) -> ExtractedDocument:
    """Create a synthetic extracted document for chunking tests."""

    return ExtractedDocument(
        document_id="document-001",
        file_name="synthetic-proposal.pdf",
        file_path=Path("/tmp/synthetic-proposal.pdf"),
        document_type=DocumentType.PDF,
        mime_type="application/pdf",
        checksum_sha256="a" * 64,
        page_count=len(pages),
        pages=[
            DocumentPage(
                page_number=index + 1,
                text=text,
                width=612,
                height=792,
            )
            for index, text in enumerate(pages)
        ],
        metadata=DocumentMetadata(
            title="Synthetic Proposal",
        ),
    )


def test_chunker_creates_one_chunk_for_short_page() -> None:
    document = create_document(
        pages=[
            "The implementation duration is twelve months.",
        ]
    )
    chunker = PageAwareDocumentChunker(
        max_characters=200,
        overlap_characters=20,
    )

    result = chunker.chunk(document)

    assert result.chunk_count == 1
    assert result.pages_with_chunks == 1
    assert result.chunks[0].text == ("The implementation duration is twelve months.")
    assert result.chunks[0].page_number == 1
    assert result.chunks[0].page_chunk_index == 0
    assert result.chunks[0].document_chunk_index == 0


def test_chunker_never_crosses_page_boundaries() -> None:
    document = create_document(
        pages=[
            "First page delivery information.",
            "Second page commercial information.",
        ]
    )
    chunker = PageAwareDocumentChunker(
        max_characters=200,
        overlap_characters=20,
    )

    result = chunker.chunk(document)

    assert result.chunk_count == 2

    assert result.chunks[0].page_number == 1
    assert "First page" in result.chunks[0].text
    assert "Second page" not in result.chunks[0].text

    assert result.chunks[1].page_number == 2
    assert "Second page" in result.chunks[1].text
    assert "First page" not in result.chunks[1].text


def test_chunker_splits_long_page() -> None:
    text = " ".join(
        [f"Sentence number {index} contains proposal information." for index in range(30)]
    )
    document = create_document(
        pages=[text],
    )
    chunker = PageAwareDocumentChunker(
        max_characters=250,
        overlap_characters=40,
    )

    result = chunker.chunk(document)

    assert result.chunk_count > 1
    assert all(chunk.character_count <= 250 for chunk in result.chunks)
    assert all(chunk.page_number == 1 for chunk in result.chunks)


def test_chunker_preserves_citation_metadata() -> None:
    document = create_document(
        pages=[
            "The proposed support period is three years.",
        ]
    )
    chunker = PageAwareDocumentChunker(
        max_characters=200,
        overlap_characters=20,
    )

    result = chunker.chunk(document)
    citation = result.chunks[0].citation

    assert citation.document_id == "document-001"
    assert citation.file_name == "synthetic-proposal.pdf"
    assert citation.page_number == 1
    assert citation.checksum_sha256 == "a" * 64
    assert citation.label == ("synthetic-proposal.pdf, page 1")


def test_chunker_assigns_stable_chunk_order() -> None:
    document = create_document(
        pages=[
            "Page one content.",
            "Page two content.",
            "Page three content.",
        ]
    )
    chunker = PageAwareDocumentChunker(
        max_characters=200,
        overlap_characters=20,
    )

    result = chunker.chunk(document)

    assert [chunk.document_chunk_index for chunk in result.chunks] == [0, 1, 2]

    assert [chunk.page_chunk_index for chunk in result.chunks] == [0, 0, 0]


def test_chunker_skips_empty_pages() -> None:
    document = create_document(
        pages=[
            "Page one content.",
            "   ",
            "Page three content.",
        ]
    )
    chunker = PageAwareDocumentChunker(
        max_characters=200,
        overlap_characters=20,
    )

    result = chunker.chunk(document)

    assert result.chunk_count == 2
    assert result.pages_with_chunks == 2
    assert [chunk.page_number for chunk in result.chunks] == [1, 3]


def test_chunking_service_uses_configured_chunker() -> None:
    document = create_document(
        pages=[
            "Synthetic proposal content.",
        ]
    )
    chunker = PageAwareDocumentChunker(
        max_characters=200,
        overlap_characters=20,
    )
    service = DocumentChunkingService(
        chunker=chunker,
    )

    result = service.chunk_document(document)

    assert result.document_id == "document-001"
    assert result.chunk_count == 1


@pytest.mark.parametrize(
    ("max_characters", "overlap_characters", "error_message"),
    [
        (
            99,
            10,
            "max_characters must be at least 100",
        ),
        (
            200,
            -1,
            "overlap_characters cannot be negative",
        ),
        (
            200,
            200,
            "overlap_characters must be smaller",
        ),
        (
            200,
            250,
            "overlap_characters must be smaller",
        ),
    ],
)
def test_chunker_rejects_invalid_configuration(
    max_characters: int,
    overlap_characters: int,
    error_message: str,
) -> None:
    with pytest.raises(
        InvalidChunkingConfigurationError,
        match=error_message,
    ):
        PageAwareDocumentChunker(
            max_characters=max_characters,
            overlap_characters=overlap_characters,
        )
