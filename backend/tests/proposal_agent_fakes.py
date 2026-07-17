from pydantic import BaseModel, Field

from app.tools.base import BaseTool


class FakeSearchEvidenceInput(BaseModel):
    """Input accepted by the fake evidence-search tool."""

    query: str = Field(min_length=1)


class FakeSearchEvidenceOutput(BaseModel):
    """Output returned by the fake evidence-search tool."""

    response: dict[str, object]


class FakeSearchEvidenceTool(BaseTool):
    """Deterministic evidence-search tool for agent tests."""

    def __init__(self) -> None:
        self.received_queries: list[str] = []

    @property
    def name(self) -> str:
        """Return the fake tool name."""

        return "search_evidence"

    @property
    def description(self) -> str:
        """Return the fake tool description."""

        return "Search synthetic proposal evidence."

    @property
    def input_model(self) -> type:
        """Return the input schema."""

        return FakeSearchEvidenceInput

    @property
    def output_model(self) -> type:
        """Return the output schema."""

        return FakeSearchEvidenceOutput

    @property
    def allowed_agents(self) -> tuple[str, ...]:
        """Return agents permitted to use the fake tool."""

        return ("proposal-analysis",)

    def execute(
        self,
        tool_input: BaseModel,
    ) -> BaseModel:
        """Return deterministic synthetic proposal evidence."""

        validated_input = FakeSearchEvidenceInput.model_validate(
            tool_input,
        )

        self.received_queries.append(
            validated_input.query,
        )

        return FakeSearchEvidenceOutput(
            response={
                "query": validated_input.query,
                "candidates": [
                    {
                        "chunk": {
                            "chunk_id": "chunk-001",
                            "document_id": "proposal-001",
                            "text": ("The implementation timeline is twelve months."),
                            "page_number": 4,
                            "page_chunk_index": 0,
                            "document_chunk_index": 0,
                            "citation": {
                                "document_id": "proposal-001",
                                "file_name": ("synthetic-proposal.pdf"),
                                "page_number": 4,
                                "checksum_sha256": "a" * 64,
                            },
                            "metadata": {},
                        },
                        "retrieval_score": 0.88,
                        "retrieval_rank": 1,
                        "reranking_score": 1.0,
                        "final_score": 0.92,
                        "duplicate_chunk_ids": [],
                        "metadata": {},
                        "citation_label": ("synthetic-proposal.pdf, page 4"),
                        "duplicate_count": 0,
                    }
                ],
                "metrics": {
                    "initial_candidate_count": 1,
                    "deduplicated_candidate_count": 1,
                    "duplicate_count": 0,
                    "reranked_candidate_count": 1,
                    "final_result_count": 1,
                    "embedding_latency_ms": 0.1,
                    "vector_search_latency_ms": 0.1,
                    "deduplication_latency_ms": 0.1,
                    "reranking_latency_ms": 0.1,
                    "total_latency_ms": 0.4,
                },
                "result_count": 1,
            }
        )
