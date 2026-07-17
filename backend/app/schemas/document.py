from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, computed_field


class DocumentType(StrEnum):
    """Document types currently supported by the platform."""

    PDF = "pdf"


class DocumentMetadata(BaseModel):
    """Metadata extracted from a source document."""

    title: str | None = None
    author: str | None = None
    subject: str | None = None
    creator: str | None = None
    producer: str | None = None


class DocumentPage(BaseModel):
    """Text and dimensions extracted from one document page."""

    page_number: int = Field(ge=1)
    text: str
    width: float | None = Field(default=None, ge=0)
    height: float | None = Field(default=None, ge=0)

    @computed_field
    @property
    def character_count(self) -> int:
        """Return the number of characters extracted from the page."""

        return len(self.text)

    @computed_field
    @property
    def has_text(self) -> bool:
        """Return whether the page contains extractable text."""

        return bool(self.text.strip())


class ExtractedDocument(BaseModel):
    """Provider-independent representation of an extracted document."""

    document_id: str
    file_name: str
    file_path: Path
    document_type: DocumentType
    mime_type: str
    checksum_sha256: str

    page_count: int = Field(ge=1)
    pages: list[DocumentPage] = Field(min_length=1)

    metadata: DocumentMetadata = Field(
        default_factory=DocumentMetadata,
    )

    @computed_field
    @property
    def full_text(self) -> str:
        """Join extracted text while preserving page boundaries."""

        return "\n\n".join(
            page.text
            for page in self.pages
            if page.text.strip()
        )

    @computed_field
    @property
    def extracted_character_count(self) -> int:
        """Return the total number of extracted characters."""

        return sum(
            page.character_count
            for page in self.pages
        )

    @computed_field
    @property
    def text_page_count(self) -> int:
        """Return the number of pages containing extractable text."""

        return sum(
            1
            for page in self.pages
            if page.has_text
        )