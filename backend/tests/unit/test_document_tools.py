from pathlib import Path
from typing import Any

import pytest

from app.core.exceptions import ToolExecutionError
from app.documents.parsers.pdf import PypdfPDFParser
from app.documents.registry import DocumentParserRegistry
from app.rag.chunking import PageAwareDocumentChunker
from app.services.document_chunking_service import (
    DocumentChunkingService,
)
from app.services.document_extraction_service import (
    DocumentExtractionService,
)
from app.tools.document_tools import (
    ChunkDocumentTool,
    ExtractDocumentTool,
    GetDocumentPageTool,
)
from app.tools.registry import ToolRegistry
from tests.fixtures.pdf_factory import create_test_pdf


def create_extraction_service() -> DocumentExtractionService:
    """Create a PDF extraction service for document-tool tests."""

    registry = DocumentParserRegistry()
    registry.register(PypdfPDFParser())

    return DocumentExtractionService(
        registry=registry,
    )


def create_chunking_service() -> DocumentChunkingService:
    """Create a page-aware chunking service for tests."""

    return DocumentChunkingService(
        chunker=PageAwareDocumentChunker(
            max_characters=200,
            overlap_characters=20,
        )
    )


def extract_document_output(
    tmp_path: Path,
) -> dict[str, Any]:
    """Extract a synthetic PDF and return its serialized output."""

    pdf_path = create_test_pdf(
        file_path=tmp_path / "proposal.pdf",
        pages=[
            "The delivery timeline is twelve months.",
            "The support period is three years.",
        ],
    )

    tool = ExtractDocumentTool(
        extraction_service=create_extraction_service(),
    )

    result = tool.run(
        payload={
            "file_path": str(pdf_path),
        }
    )

    assert result.output is not None

    return result.output


def test_extract_document_tool_extracts_pdf(
    tmp_path: Path,
) -> None:
    pdf_path = create_test_pdf(
        file_path=tmp_path / "proposal.pdf",
        pages=[
            "The delivery timeline is twelve months.",
            "The support period is three years.",
        ],
    )

    tool = ExtractDocumentTool(
        extraction_service=create_extraction_service(),
    )

    result = tool.run(
        payload={
            "file_path": str(pdf_path),
        },
        metadata={
            "assessment_id": "assessment-001",
        },
    )

    assert result.succeeded
    assert result.output is not None
    assert result.output["document"]["file_name"] == ("proposal.pdf")
    assert result.output["document"]["page_count"] == 2
    assert result.metadata["assessment_id"] == "assessment-001"


def test_extract_document_tool_exposes_permissions() -> None:
    tool = ExtractDocumentTool(
        extraction_service=create_extraction_service(),
    )

    assert tool.allowed_agents == (
        "orchestrator",
        "proposal-analysis",
    )


def test_chunk_document_tool_creates_cited_chunks(
    tmp_path: Path,
) -> None:
    extracted_output = extract_document_output(tmp_path)

    tool = ChunkDocumentTool(
        chunking_service=create_chunking_service(),
    )

    result = tool.run(
        payload={
            "document": extracted_output["document"],
        }
    )

    assert result.succeeded
    assert result.output is not None
    assert result.output["result"]["chunk_count"] == 2

    first_chunk = result.output["result"]["chunks"][0]

    assert first_chunk["page_number"] == 1
    assert first_chunk["citation"]["file_name"] == ("proposal.pdf")
    assert first_chunk["citation"]["page_number"] == 1


def test_get_document_page_tool_returns_requested_page(
    tmp_path: Path,
) -> None:
    extracted_output = extract_document_output(tmp_path)

    tool = GetDocumentPageTool()

    result = tool.run(
        payload={
            "document": extracted_output["document"],
            "page_number": 2,
        }
    )

    assert result.succeeded
    assert result.output is not None
    assert result.output["page"]["page_number"] == 2
    assert "three years" in result.output["page"]["text"]
    assert result.output["citation"]["label"] == ("proposal.pdf, page 2")


def test_get_document_page_tool_rejects_missing_page(
    tmp_path: Path,
) -> None:
    extracted_output = extract_document_output(tmp_path)

    tool = GetDocumentPageTool()

    with pytest.raises(
        ToolExecutionError,
        match="execution failed",
    ):
        tool.run(
            payload={
                "document": extracted_output["document"],
                "page_number": 99,
            }
        )


def test_registry_enforces_document_tool_permissions(
    tmp_path: Path,
) -> None:
    pdf_path = create_test_pdf(
        file_path=tmp_path / "proposal.pdf",
        pages=["Synthetic proposal content."],
    )

    registry = ToolRegistry()
    registry.register(
        ExtractDocumentTool(
            extraction_service=create_extraction_service(),
        )
    )

    result = registry.execute(
        tool_name="extract_document",
        payload={
            "file_path": str(pdf_path),
        },
        agent_name="proposal-analysis",
    )

    assert result.succeeded
    assert result.metadata["agent_name"] == ("proposal-analysis")
