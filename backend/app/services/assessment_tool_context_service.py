from app.services.assessment_retrieval_context_service import (
    AssessmentRetrievalContextService,
)
from app.tools.registry import ToolRegistry
from app.tools.retrieval_tools import SearchEvidenceTool


class AgentScopedSearchEvidenceTool(SearchEvidenceTool):
    """Evidence search tool restricted to one specialist agent."""

    def __init__(
        self,
        retrieval_service: object,
        allowed_agent: str,
    ) -> None:
        super().__init__(retrieval_service=retrieval_service)
        self._allowed_agent = allowed_agent

    @property
    def allowed_agents(self) -> tuple[str, ...]:
        """Return the only specialist agent permitted to use this tool."""

        return (self._allowed_agent,)


class AssessmentToolContextService:
    """Create bounded, assessment-scoped specialist tool registries."""

    def __init__(
        self,
        retrieval_context_service: AssessmentRetrievalContextService,
    ) -> None:
        self._retrieval_context_service = retrieval_context_service

    async def create_proposal_analysis_registry(
        self,
        assessment_id: str,
    ) -> ToolRegistry:
        """Create a proposal-analysis registry for one assessment."""

        return await self._create_registry(
            assessment_id=assessment_id,
            allowed_agent="proposal-analysis",
        )

    async def create_vendor_research_registry(
        self,
        assessment_id: str,
    ) -> ToolRegistry:
        """Create a vendor-research registry for one assessment."""

        return await self._create_registry(
            assessment_id=assessment_id,
            allowed_agent="vendor-research",
        )

    async def _create_registry(
        self,
        assessment_id: str,
        allowed_agent: str,
    ) -> ToolRegistry:
        """Create one registry containing only scoped evidence search."""

        retrieval_service = await self._retrieval_context_service.create_retrieval_service(
            assessment_id
        )

        registry = ToolRegistry()
        registry.register(
            AgentScopedSearchEvidenceTool(
                retrieval_service=retrieval_service,
                allowed_agent=allowed_agent,
            )
        )
        return registry
