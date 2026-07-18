from app.services.assessment_retrieval_context_service import (
    AssessmentRetrievalContextService,
)
from app.services.retrieval_service import RetrievalService
from app.tools.registry import ToolRegistry
from app.tools.retrieval_tools import SearchEvidenceTool


class AgentScopedSearchEvidenceTool(SearchEvidenceTool):
    """Evidence search tool restricted to one specialist agent."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        allowed_agent: str,
    ) -> None:
        super().__init__(retrieval_service=retrieval_service)
        self._allowed_agent = allowed_agent

    @property
    def allowed_agents(self) -> tuple[str, ...]:
        """Return the only agent permitted to use this tool."""

        return (self._allowed_agent,)


class AssessmentToolContextService:
    """Create purpose and assessment-scoped specialist registries."""

    def __init__(
        self,
        retrieval_context_service: AssessmentRetrievalContextService,
    ) -> None:
        self._retrieval_context_service = retrieval_context_service

    async def create_proposal_analysis_registry(
        self,
        assessment_id: str,
    ) -> ToolRegistry:
        """Create a proposal-purpose registry for one assessment."""

        retrieval_service = await self._retrieval_context_service.create_proposal_retrieval_service(
            assessment_id
        )
        return self._create_registry(
            retrieval_service=retrieval_service,
            allowed_agent="proposal-analysis",
        )

    async def create_vendor_research_registry(
        self,
        assessment_id: str,
    ) -> ToolRegistry:
        """Create a vendor-purpose registry for one assessment."""

        retrieval_service = await self._retrieval_context_service.create_vendor_retrieval_service(
            assessment_id
        )
        return self._create_registry(
            retrieval_service=retrieval_service,
            allowed_agent="vendor-research",
        )

    @staticmethod
    def _create_registry(
        retrieval_service: RetrievalService,
        allowed_agent: str,
    ) -> ToolRegistry:
        """Create one registry containing only bounded evidence search."""

        registry = ToolRegistry()
        registry.register(
            AgentScopedSearchEvidenceTool(
                retrieval_service=retrieval_service,
                allowed_agent=allowed_agent,
            )
        )
        return registry
