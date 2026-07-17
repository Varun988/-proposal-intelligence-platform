from pydantic import BaseModel, Field, computed_field


class ChunkCitation(BaseModel):
    """Citation metadata connecting a chunk to its source document."""

    document_id: str
    file_name: str
    page_number: int = Field(ge=1)
    checksum_sha256: str

    @computed_field
    @property
    def label(self) -> str:
        """Return a human-readable citation label."""

        return f"{self.file_name}, page {self.page_number}"


class DocumentChunk(BaseModel):
    """A retrieval-ready text chunk from one document page."""

    chunk_id: str
    document_id: str
    text: str = Field(min_length=1)

    page_number: int = Field(ge=1)
    page_chunk_index: int = Field(ge=0)
    document_chunk_index: int = Field(ge=0)

    citation: ChunkCitation

    metadata: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict,
    )

    @computed_field
    @property
    def character_count(self) -> int:
        """Return the number of characters in the chunk."""

        return len(self.text)


class ChunkingResult(BaseModel):
    """Result of chunking one extracted document."""

    document_id: str
    chunks: list[DocumentChunk]
    source_character_count: int = Field(ge=0)
    chunk_character_count: int = Field(ge=0)

    @computed_field
    @property
    def chunk_count(self) -> int:
        """Return the number of generated chunks."""

        return len(self.chunks)

    @computed_field
    @property
    def pages_with_chunks(self) -> int:
        """Return the number of unique pages represented by chunks."""

        return len({chunk.page_number for chunk in self.chunks})
