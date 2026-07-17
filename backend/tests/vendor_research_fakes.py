from pydantic import BaseModel, Field

from app.tools.base import BaseTool


class FakeVendorSearchInput(BaseModel):
    """Input accepted by the fake vendor search tool."""

    query: str = Field(min_length=1)


class FakeVendorSearchOutput(BaseModel):
    """Output returned by the fake vendor search tool."""

    response: dict[str, object]


class FakeVendorSearchTool(BaseTool):
    """Return deterministic approved vendor evidence."""

    def __init__(self) -> None:
        self.received_queries: list[str] = []

    @property
    def name(self) -> str:
        return "search_evidence"

    @property
    def description(self) -> str:
        return "Search approved synthetic vendor evidence."

    @property
    def input_model(self) -> type:
        return FakeVendorSearchInput

    @property
    def output_model(self) -> type:
        return FakeVendorSearchOutput

    @property
    def allowed_agents(self) -> tuple[str, ...]:
        return ("vendor-research",)

    def execute(
        self,
        tool_input: BaseModel,
    ) -> BaseModel:
        validated_input = FakeVendorSearchInput.model_validate(
            tool_input,
        )

        self.received_queries.append(
            validated_input.query,
        )

        return FakeVendorSearchOutput(
            response={
                "query": validated_input.query,
                "candidates": [
                    {
                        "chunk": {
                            "chunk_id": "vendor-profile-chunk",
                            "document_id": "vendor-profile-001",
                            "text": ("Example Digital Services was established in 2012."),
                            "page_number": 2,
                            "page_chunk_index": 0,
                            "document_chunk_index": 0,
                            "citation": {
                                "document_id": ("vendor-profile-001"),
                                "file_name": ("synthetic-vendor-profile.pdf"),
                                "page_number": 2,
                                "checksum_sha256": "a" * 64,
                            },
                            "metadata": {
                                "source_type": ("synthetic_profile"),
                                "evidence_category": ("company_profile"),
                                "source_name": ("Synthetic Vendor Profile"),
                                "publication_date": "2026-01-01",
                                "retrieved_date": "2026-07-17",
                            },
                        },
                        "retrieval_score": 0.90,
                        "retrieval_rank": 1,
                        "reranking_score": 1.0,
                        "final_score": 0.95,
                        "duplicate_chunk_ids": [],
                        "metadata": {},
                        "citation_label": ("synthetic-vendor-profile.pdf, page 2"),
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
