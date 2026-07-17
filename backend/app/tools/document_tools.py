from pathlib import Path

from pydantic import BaseModel, Field

from app.core.exceptions import DocumentNotFoundError
from app.services.document_chunking_service import (
    DocumentChunkingService,
)
from app.services.document_extraction_service import (
    DocumentExtractionService,
)
from app.schemas.chunk import (
    ChunkCitation,
    ChunkingResult,
)
from app.schemas.document import (
    DocumentPage,
    ExtractedDocument,
)
from app.tools.base import BaseTool


class ExtractDocumentInput(BaseModel):
    """Input accepted by the document-extraction tool."""

    file_path: Path


class ExtractDocumentOutput(BaseModel):
    """Output returned by the document-extraction tool."""

    document: ExtractedDocument


class ChunkDocumentInput(BaseModel):
    """Input accepted by the document-chunking tool."""

    document: ExtractedDocument


class ChunkDocumentOutput(BaseModel):
    """Output returned by the document-chunking tool."""

    result: ChunkingResult


class GetDocumentPageInput(BaseModel):
    """Input accepted by the page-retrieval tool."""

    document: ExtractedDocument
    page_number: int = Field(ge=1)


class GetDocumentPageOutput(BaseModel):
    """Output returned by the page-retrieval tool."""

    document_id: str
    file_name: str
    page: DocumentPage
    citation: ChunkCitation


class ExtractDocumentTool(BaseTool):
    """Extract structured content from a supported document."""

    def __init__(
        self,
        extraction_service: DocumentExtractionService,
    ) -> None:
        self._extraction_service = extraction_service

    @property
    def name(self) -> str:
        return "extract_document"

    @property
    def description(self) -> str:
        return (
            "Extract page-aware text, metadata, and checksum information from a supported document."
        )

    @property
    def input_model(self) -> type:
        return ExtractDocumentInput

    @property
    def output_model(self) -> type:
        return ExtractDocumentOutput

    @property
    def allowed_agents(self) -> tuple[str, ...]:
        return (
            "orchestrator",
            "proposal-analysis",
        )

    def execute(
        self,
        tool_input: BaseModel,
    ) -> BaseModel:
        validated_input = ExtractDocumentInput.model_validate(
            tool_input,
        )

        document = self._extraction_service.extract(
            validated_input.file_path,
        )

        return ExtractDocumentOutput(
            document=document,
        )


class ChunkDocumentTool(BaseTool):
    """Convert an extracted document into page-aware chunks."""

    def __init__(
        self,
        chunking_service: DocumentChunkingService,
    ) -> None:
        self._chunking_service = chunking_service

    @property
    def name(self) -> str:
        return "chunk_document"

    @property
    def description(self) -> str:
        return "Convert an extracted document into page-aware, citation-ready retrieval chunks."

    @property
    def input_model(self) -> type:
        return ChunkDocumentInput

    @property
    def output_model(self) -> type:
        return ChunkDocumentOutput

    @property
    def allowed_agents(self) -> tuple[str, ...]:
        return (
            "orchestrator",
            "proposal-analysis",
        )

    def execute(
        self,
        tool_input: BaseModel,
    ) -> BaseModel:
        validated_input = ChunkDocumentInput.model_validate(
            tool_input,
        )

        result = self._chunking_service.chunk_document(
            validated_input.document,
        )

        return ChunkDocumentOutput(
            result=result,
        )


class GetDocumentPageTool(BaseTool):
    """Return one page and its citation from an extracted document."""

    @property
    def name(self) -> str:
        return "get_document_page"

    @property
    def description(self) -> str:
        return "Retrieve a specific page from an extracted document with source citation metadata."

    @property
    def input_model(self) -> type:
        return GetDocumentPageInput

    @property
    def output_model(self) -> type:
        return GetDocumentPageOutput

    @property
    def allowed_agents(self) -> tuple[str, ...]:
        return (
            "orchestrator",
            "proposal-analysis",
            "risk-report",
        )

    def execute(
        self,
        tool_input: BaseModel,
    ) -> BaseModel:
        validated_input = GetDocumentPageInput.model_validate(
            tool_input,
        )

        matching_page = next(
            (
                page
                for page in validated_input.document.pages
                if page.page_number == validated_input.page_number
            ),
            None,
        )

        if matching_page is None:
            raise DocumentNotFoundError(
                "Requested page was not found in document "
                f"'{validated_input.document.file_name}': "
                f"{validated_input.page_number}."
            )

        citation = ChunkCitation(
            document_id=validated_input.document.document_id,
            file_name=validated_input.document.file_name,
            page_number=matching_page.page_number,
            checksum_sha256=(validated_input.document.checksum_sha256),
        )

        return GetDocumentPageOutput(
            document_id=validated_input.document.document_id,
            file_name=validated_input.document.file_name,
            page=matching_page,
            citation=citation,
        )
