from collections.abc import Callable
from typing import Protocol

from app.agents.orchestrator.agent import OrchestratorAgent
from app.agents.proposal_analysis.agent import ProposalAnalysisAgent
from app.agents.risk_report.agent import RiskReportAgent
from app.agents.vendor_research.agent import VendorResearchAgent
from app.evaluation.proposal_analysis import (
    create_proposal_analysis_evaluation_runner,
)
from app.evaluation.risk_report import create_risk_report_evaluation_runner
from app.evaluation.vendor_research import (
    create_vendor_research_evaluation_runner,
)
from app.services.assessment_tool_context_service import (
    AssessmentToolContextService,
)
from app.services.llm_service import LLMService
from app.workflows.assessment_graph import create_assessment_graph
from app.workflows.executor import LangGraphAssessmentWorkflowExecutor
from app.workflows.state import AssessmentWorkflowState


class AssessmentExecutorProtocol(Protocol):
    """Minimum executor returned by the runtime factory."""

    async def execute(
        self,
        state: AssessmentWorkflowState,
    ) -> AssessmentWorkflowState:
        """Execute one assessment workflow."""


class AssessmentRuntimeFactoryProtocol(Protocol):
    """Factory contract for assessment-specific workflow executors."""

    async def create_executor(
        self,
        assessment_id: str,
    ) -> AssessmentExecutorProtocol:
        """Create an executor scoped to one assessment."""


class AssessmentWorkflowRuntimeFactory:
    """Build a real four-agent runtime for one assessment."""

    def __init__(
        self,
        tool_context_service: AssessmentToolContextService,
        llm_service_factory: Callable[[], LLMService],
        proposal_max_tool_calls: int = 6,
        vendor_max_tool_calls: int = 6,
    ) -> None:
        if proposal_max_tool_calls < 1:
            raise ValueError("Proposal Analysis maximum tool calls must be at least one.")
        if vendor_max_tool_calls < 1:
            raise ValueError("Vendor Research maximum tool calls must be at least one.")

        self._tool_context_service = tool_context_service
        self._llm_service_factory = llm_service_factory
        self._proposal_max_tool_calls = proposal_max_tool_calls
        self._vendor_max_tool_calls = vendor_max_tool_calls

    async def create_executor(
        self,
        assessment_id: str,
    ) -> LangGraphAssessmentWorkflowExecutor:
        """Create a fresh graph with assessment-scoped retrieval tools."""

        normalized_id = assessment_id.strip()
        if not normalized_id:
            raise ValueError("Assessment ID is required for workflow runtime.")

        proposal_registry = await self._tool_context_service.create_proposal_analysis_registry(
            normalized_id
        )
        vendor_registry = await self._tool_context_service.create_vendor_research_registry(
            normalized_id
        )

        llm_service = self._llm_service_factory()

        graph = create_assessment_graph(
            orchestrator_agent=OrchestratorAgent(),
            proposal_analysis_agent=ProposalAnalysisAgent(
                tool_registry=proposal_registry,
                llm_service=llm_service,
                max_tool_calls=self._proposal_max_tool_calls,
            ),
            proposal_evaluation_runner=(create_proposal_analysis_evaluation_runner()),
            vendor_research_agent=VendorResearchAgent(
                tool_registry=vendor_registry,
                llm_service=llm_service,
                max_tool_calls=self._vendor_max_tool_calls,
            ),
            vendor_evaluation_runner=(create_vendor_research_evaluation_runner()),
            risk_report_agent=RiskReportAgent(
                llm_service=llm_service,
            ),
            risk_report_evaluation_runner=(create_risk_report_evaluation_runner()),
        )

        return LangGraphAssessmentWorkflowExecutor(graph=graph)


class DynamicAssessmentWorkflowExecutor:
    """Create and run a fresh assessment-scoped executor per execution."""

    def __init__(
        self,
        runtime_factory: AssessmentRuntimeFactoryProtocol,
    ) -> None:
        self._runtime_factory = runtime_factory

    async def execute(
        self,
        state: AssessmentWorkflowState,
    ) -> AssessmentWorkflowState:
        """Build the runtime from the state's assessment identity and run it."""

        executor = await self._runtime_factory.create_executor(state.assessment_id)
        return await executor.execute(state.model_copy(deep=True))
