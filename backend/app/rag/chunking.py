import re
from uuid import uuid4

from app.core.exceptions import (
    InvalidChunkingConfigurationError,
)
from app.rag.base import BaseDocumentChunker
from app.schemas.chunk import (
    ChunkCitation,
    ChunkingResult,
    DocumentChunk,
)
from app.schemas.document import (
    DocumentPage,
    ExtractedDocument,
)


class PageAwareDocumentChunker(BaseDocumentChunker):
    """Create overlapping chunks without crossing page boundaries."""

    def __init__(
        self,
        max_characters: int = 1_500,
        overlap_characters: int = 200,
    ) -> None:
        if max_characters < 100:
            raise InvalidChunkingConfigurationError("max_characters must be at least 100.")

        if overlap_characters < 0:
            raise InvalidChunkingConfigurationError("overlap_characters cannot be negative.")

        if overlap_characters >= max_characters:
            raise InvalidChunkingConfigurationError(
                "overlap_characters must be smaller than max_characters."
            )

        self._max_characters = max_characters
        self._overlap_characters = overlap_characters

    @property
    def max_characters(self) -> int:
        """Return the configured maximum chunk size."""

        return self._max_characters

    @property
    def overlap_characters(self) -> int:
        """Return the configured chunk overlap."""

        return self._overlap_characters

    def chunk(
        self,
        document: ExtractedDocument,
    ) -> ChunkingResult:
        """Create page-aware chunks from an extracted document."""

        document_chunks: list[DocumentChunk] = []
        document_chunk_index = 0

        for page in document.pages:
            page_texts = self._chunk_page(page)

            for page_chunk_index, text in enumerate(page_texts):
                citation = ChunkCitation(
                    document_id=document.document_id,
                    file_name=document.file_name,
                    page_number=page.page_number,
                    checksum_sha256=document.checksum_sha256,
                )

                document_chunks.append(
                    DocumentChunk(
                        chunk_id=str(uuid4()),
                        document_id=document.document_id,
                        text=text,
                        page_number=page.page_number,
                        page_chunk_index=page_chunk_index,
                        document_chunk_index=document_chunk_index,
                        citation=citation,
                        metadata={
                            "document_type": (document.document_type.value),
                            "mime_type": document.mime_type,
                            "source_file": document.file_name,
                            "page_number": page.page_number,
                        },
                    )
                )

                document_chunk_index += 1

        chunk_character_count = sum(chunk.character_count for chunk in document_chunks)

        return ChunkingResult(
            document_id=document.document_id,
            chunks=document_chunks,
            source_character_count=(document.extracted_character_count),
            chunk_character_count=chunk_character_count,
        )

    def _chunk_page(
        self,
        page: DocumentPage,
    ) -> list:
        """Split one page without crossing its boundary."""

        normalized_text = self._normalize_text(page.text)

        if not normalized_text:
            return []

        if len(normalized_text) <= self._max_characters:
            return [normalized_text]

        chunks: list[str] = []
        start = 0
        text_length = len(normalized_text)

        while start < text_length:
            preferred_end = min(
                start + self._max_characters,
                text_length,
            )

            end = self._find_chunk_end(
                text=normalized_text,
                start=start,
                preferred_end=preferred_end,
            )

            chunk_text = normalized_text[start:end].strip()

            if chunk_text:
                chunks.append(chunk_text)

            if end >= text_length:
                break

            next_start = max(
                end - self._overlap_characters,
                start + 1,
            )

            start = self._skip_leading_whitespace(
                text=normalized_text,
                position=next_start,
            )

        return chunks

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize line spacing while retaining paragraphs."""

        normalized_lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]

        normalized_text = "\n".join(normalized_lines)

        normalized_text = re.sub(
            r"\n{3,}",
            "\n\n",
            normalized_text,
        )

        normalized_text = re.sub(
            r"[ \t]+",
            " ",
            normalized_text,
        )

        return normalized_text.strip()

    @staticmethod
    def _find_chunk_end(
        text: str,
        start: int,
        preferred_end: int,
    ) -> int:
        """Find a readable boundary at or before the preferred end."""

        if preferred_end >= len(text):
            return len(text)

        minimum_boundary = start + int((preferred_end - start) * 0.6)

        boundary_candidates = [
            text.rfind("\n\n", minimum_boundary, preferred_end),
            text.rfind(". ", minimum_boundary, preferred_end),
            text.rfind("\n", minimum_boundary, preferred_end),
            text.rfind(" ", minimum_boundary, preferred_end),
        ]

        valid_candidates = [
            candidate for candidate in boundary_candidates if candidate >= minimum_boundary
        ]

        if not valid_candidates:
            return preferred_end

        selected_boundary = max(valid_candidates)

        if text.startswith("\n\n", selected_boundary):
            return selected_boundary + 2

        if text.startswith(". ", selected_boundary):
            return selected_boundary + 1

        return selected_boundary

    @staticmethod
    def _skip_leading_whitespace(
        text: str,
        position: int,
    ) -> int:
        """Move a position past any leading whitespace."""

        while position < len(text) and text[position].isspace():
            position += 1

        return position
