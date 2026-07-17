from pydantic import BaseModel, Field


class AssessmentVectorIndexMetadata(BaseModel):
    """Metadata describing one assessment-scoped vector index."""

    assessment_id: str = Field(min_length=1)

    document_ids: list[str] = Field(
        default_factory=list,
    )

    indexed_chunk_count: int = Field(
        default=0,
        ge=0,
    )

    embedding_provider: str = Field(min_length=1)
    embedding_model: str = Field(min_length=1)

    vector_dimension: int = Field(ge=1)
    vector_store_size: int = Field(ge=0)


class DocumentIndexingResult(BaseModel):
    """Result returned after indexing one document."""

    assessment_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)

    indexed_chunk_count: int = Field(ge=1)
    vector_store_size: int = Field(ge=1)
    vector_dimension: int = Field(ge=1)

    embedding_provider: str = Field(min_length=1)
    embedding_model: str = Field(min_length=1)
