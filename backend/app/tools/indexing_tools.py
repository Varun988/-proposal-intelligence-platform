from pydantic import BaseModel, Field

from app.rag.vector_store.base import BaseVectorStore
from app.schemas.chunk import DocumentChunk
from app.services.embedding_service import EmbeddingService
from app.tools.base import BaseTool


class IndexDocumentInput(BaseModel):
    """Input accepted by the document-indexing tool."""

    chunks: list[DocumentChunk] = Field(min_length=1)


class IndexDocumentOutput(BaseModel):
    """Output returned after indexing document chunks."""

    indexed_chunk_count: int = Field(ge=0)
    vector_store_size: int = Field(ge=0)
    vector_dimension: int = Field(ge=1)
    embedding_provider: str = Field(min_length=1)
    embedding_model: str = Field(min_length=1)


class IndexDocumentTool(BaseTool):
    """Generate embeddings and index document chunks."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: BaseVectorStore,
    ) -> None:
        self._embedding_service = embedding_service
        self._vector_store = vector_store

    @property
    def name(self) -> str:
        """Return the unique tool name."""

        return "index_document"

    @property
    def description(self) -> str:
        """Return the tool description."""

        return (
            "Generate embeddings for citation-ready document chunks "
            "and add them to the configured vector store."
        )

    @property
    def input_model(self) -> type:
        """Return the tool input schema."""

        return IndexDocumentInput

    @property
    def output_model(self) -> type:
        """Return the tool output schema."""

        return IndexDocumentOutput

    @property
    def allowed_agents(self) -> tuple[str, ...]:
        """Return agents permitted to index documents."""

        return (
            "orchestrator",
            "proposal-analysis",
        )

    def execute(
        self,
        tool_input: BaseModel,
    ) -> BaseModel:
        """Embed and index supplied document chunks."""

        validated_input = IndexDocumentInput.model_validate(
            tool_input,
        )

        embedding_result = self._embedding_service.embed_chunks(
            validated_input.chunks,
        )

        self._vector_store.add(
            embedding_result.items,
        )

        return IndexDocumentOutput(
            indexed_chunk_count=embedding_result.item_count,
            vector_store_size=self._vector_store.size,
            vector_dimension=self._vector_store.dimension,
            embedding_provider=embedding_result.provider_name,
            embedding_model=embedding_result.model_name,
        )
