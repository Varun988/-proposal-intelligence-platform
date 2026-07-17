from pydantic import BaseModel, Field

from app.schemas.retrieval import RetrievalResponse
from app.services.retrieval_service import RetrievalService
from app.tools.base import BaseTool


class SearchEvidenceInput(BaseModel):
    """Input accepted by the evidence-search tool."""

    query: str = Field(min_length=1)


class SearchEvidenceOutput(BaseModel):
    """Output returned by the evidence-search tool."""

    response: RetrievalResponse


class SearchEvidenceTool(BaseTool):
    """Search indexed evidence using the complete retrieval pipeline."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
    ) -> None:
        self._retrieval_service = retrieval_service

    @property
    def name(self) -> str:
        """Return the unique tool name."""

        return "search_evidence"

    @property
    def description(self) -> str:
        """Return the tool description."""

        return (
            "Search indexed proposal evidence using semantic retrieval, "
            "deduplication, lexical reranking, and source citations."
        )

    @property
    def input_model(self) -> type:
        """Return the tool input schema."""

        return SearchEvidenceInput

    @property
    def output_model(self) -> type:
        """Return the tool output schema."""

        return SearchEvidenceOutput

    @property
    def allowed_agents(self) -> tuple[str, ...]:
        """Return agents permitted to search indexed evidence."""

        return (
            "orchestrator",
            "proposal-analysis",
            "risk-report",
            "vendor-research",
        )

    def execute(
        self,
        tool_input: BaseModel,
    ) -> BaseModel:
        """Execute the complete retrieval pipeline."""

        validated_input = SearchEvidenceInput.model_validate(
            tool_input,
        )

        response = self._retrieval_service.retrieve(
            validated_input.query,
        )

        return SearchEvidenceOutput(
            response=response,
        )
