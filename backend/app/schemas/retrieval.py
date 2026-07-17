from pydantic import BaseModel, Field

from app.schemas.chunk import DocumentChunk


class VectorSearchResult(BaseModel):
    """One document chunk returned by vector similarity search."""

    chunk: DocumentChunk
    score: float
    rank: int = Field(ge=1)


class VectorSearchResponse(BaseModel):
    """Ranked results returned for one vector query."""

    results: list[VectorSearchResult]
    query_dimension: int = Field(ge=1)
    total_candidates: int = Field(ge=0)
