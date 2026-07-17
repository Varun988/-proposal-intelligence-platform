import json
from time import perf_counter
from typing import Any

from pydantic import ValidationError

from app.agents.proposal_analysis.instructions import (
    PROPOSAL_ANALYSIS_INSTRUCTION_VERSION,
    PROPOSAL_ANALYSIS_SYSTEM_INSTRUCTIONS,
)
from app.agents.proposal_analysis.policies import (
    PROPOSAL_ANALYSIS_AGENT_NAME,
    PROPOSAL_ANALYSIS_ALLOWED_TOOLS,
    PROPOSAL_ANALYSIS_MAX_TOOL_CALLS,
)
from app.agents.proposal_analysis.schemas import (
    AgentToolCallTrace,
    ProposalAnalysisExecution,
    ProposalAnalysisInput,
    ProposalAnalysisResult,
)
from app.core.exceptions import (
    AgentConfigurationError,
    AgentOutputValidationError,
    AgentToolLimitError,
)
from app.schemas.llm import (
    LLMMessage,
    LLMRequest,
    MessageRole,
)
from app.services.llm_service import LLMService
from app.tools.registry import ToolRegistry


class ProposalAnalysisAgent:
    """Analyze proposal evidence through bounded tools and an LLM."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        llm_service: LLMService,
        max_tool_calls: int = PROPOSAL_ANALYSIS_MAX_TOOL_CALLS,
    ) -> None:
        if max_tool_calls < 1:
            raise AgentConfigurationError(
                "Proposal Analysis Agent must allow at least one tool call."
            )

        self._tool_registry = tool_registry
        self._llm_service = llm_service
        self._max_tool_calls = max_tool_calls

        self._validate_required_tools()

    @property
    def name(self) -> str:
        """Return the unique agent name."""

        return PROPOSAL_ANALYSIS_AGENT_NAME

    @property
    def instruction_version(self) -> str:
        """Return the active instruction version."""

        return PROPOSAL_ANALYSIS_INSTRUCTION_VERSION

    @property
    def max_tool_calls(self) -> int:
        """Return the maximum number of permitted tool calls."""

        return self._max_tool_calls

    async def analyze(
        self,
        analysis_input: ProposalAnalysisInput,
    ) -> ProposalAnalysisExecution:
        """Run an evidence-grounded proposal analysis."""

        started_at = perf_counter()

        objectives = self._build_search_objectives(
            analysis_input,
        )

        if len(objectives) > self._max_tool_calls:
            raise AgentToolLimitError(
                "Proposal analysis requires more tool calls than "
                f"the configured limit. Required: {len(objectives)}. "
                f"Allowed: {self._max_tool_calls}."
            )

        tool_traces: list[AgentToolCallTrace] = []
        retrieved_evidence: list[dict[str, Any]] = []

        for objective in objectives:
            tool_result = self._tool_registry.execute(
                tool_name="search_evidence",
                payload={
                    "query": objective,
                },
                agent_name=self.name,
                metadata={
                    "assessment_id": (analysis_input.assessment_id),
                    "proposal_document_id": (analysis_input.proposal_document_id),
                },
            )

            response_data = self._extract_retrieval_response(
                tool_result.output,
            )

            candidates = response_data.get(
                "candidates",
                [],
            )

            if not isinstance(candidates, list):
                raise AgentOutputValidationError(
                    "Evidence-search tool returned an invalid candidate collection."
                )

            retrieved_evidence.extend(candidates)

            tool_traces.append(
                AgentToolCallTrace(
                    tool_name="search_evidence",
                    query=objective,
                    succeeded=tool_result.succeeded,
                    execution_time_ms=(tool_result.execution_time_ms),
                    result_count=len(candidates),
                )
            )

        llm_request = self._build_llm_request(
            analysis_input=analysis_input,
            retrieved_evidence=retrieved_evidence,
        )

        llm_response = await self._llm_service.generate(
            assessment_id=analysis_input.assessment_id,
            request=llm_request,
        )

        result = self._validate_llm_output(
            structured_data=llm_response.structured_data,
            analysis_input=analysis_input,
        )

        return ProposalAnalysisExecution(
            result=result,
            tool_calls=tool_traces,
            tool_call_count=len(tool_traces),
            llm_provider=llm_response.provider,
            llm_model=llm_response.model,
            instruction_version=self.instruction_version,
            total_execution_time_ms=self._elapsed_ms(
                started_at,
            ),
        )

    def _validate_required_tools(self) -> None:
        """Ensure required tools are registered and permitted."""

        definitions = self._tool_registry.definitions_for_agent(
            self.name,
        )

        available_tool_names = {definition.name for definition in definitions}

        required_tools = {
            "search_evidence",
        }

        missing_tools = required_tools - available_tool_names

        if missing_tools:
            missing_text = ", ".join(sorted(missing_tools))

            raise AgentConfigurationError(
                f"Proposal Analysis Agent is missing required tools: {missing_text}."
            )

        unauthorized_tools = available_tool_names - set(PROPOSAL_ANALYSIS_ALLOWED_TOOLS)

        if unauthorized_tools:
            unauthorized_text = ", ".join(sorted(unauthorized_tools))

            raise AgentConfigurationError(
                "Proposal Analysis Agent received tools outside "
                f"its allowlist: {unauthorized_text}."
            )

    @staticmethod
    def _build_search_objectives(
        analysis_input: ProposalAnalysisInput,
    ) -> list:
        """Build focused evidence-search queries."""

        objectives = [
            (f"Find proposal evidence about {objective}.")
            for objective in analysis_input.analysis_objectives
        ]

        objectives.extend(
            (f"Find proposal evidence responding to this requirement: {requirement}")
            for requirement in analysis_input.requirements
        )

        return objectives

    @staticmethod
    def _extract_retrieval_response(
        output: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Extract the retrieval response from tool output."""

        if output is None:
            raise AgentOutputValidationError("Evidence-search tool returned no output.")

        response = output.get("response")

        if not isinstance(response, dict):
            raise AgentOutputValidationError("Evidence-search tool returned an invalid response.")

        return response

    @staticmethod
    def _build_llm_request(
        analysis_input: ProposalAnalysisInput,
        retrieved_evidence: list[dict[str, Any]],
    ) -> LLMRequest:
        """Build a structured proposal-analysis LLM request."""

        user_payload = {
            "task": ("Analyze the proposal using only the supplied retrieved evidence."),
            "analysis_input": analysis_input.model_dump(
                mode="json",
            ),
            "retrieved_evidence": retrieved_evidence,
            "output_requirements": {
                "facts_must_have_citations": True,
                "approval_decision_prohibited": True,
                "human_review_required": True,
            },
        }

        return LLMRequest(
            messages=[
                LLMMessage(
                    role=MessageRole.SYSTEM,
                    content=(PROPOSAL_ANALYSIS_SYSTEM_INSTRUCTIONS),
                ),
                LLMMessage(
                    role=MessageRole.USER,
                    content=json.dumps(
                        user_payload,
                        indent=2,
                    ),
                ),
            ],
            temperature=0.0,
            max_output_tokens=4_096,
            response_schema=(ProposalAnalysisResult.model_json_schema()),
            metadata={
                "agent_name": (PROPOSAL_ANALYSIS_AGENT_NAME),
                "instruction_version": (PROPOSAL_ANALYSIS_INSTRUCTION_VERSION),
                "assessment_id": (analysis_input.assessment_id),
            },
        )

    @staticmethod
    def _validate_llm_output(
        structured_data: dict[str, Any] | None,
        analysis_input: ProposalAnalysisInput,
    ) -> ProposalAnalysisResult:
        """Validate structured output and assessment identity."""

        if structured_data is None:
            raise AgentOutputValidationError(
                "Proposal Analysis Agent received no structured LLM output."
            )

        try:
            result = ProposalAnalysisResult.model_validate(
                structured_data,
            )
        except ValidationError as error:
            raise AgentOutputValidationError(
                "Proposal Analysis Agent returned invalid structured output."
            ) from error

        if result.assessment_id != analysis_input.assessment_id:
            raise AgentOutputValidationError(
                "Agent output assessment ID does not match the requested assessment."
            )

        if result.proposal_document_id != analysis_input.proposal_document_id:
            raise AgentOutputValidationError(
                "Agent output proposal document ID does not match the requested document."
            )

        return result

    @staticmethod
    def _elapsed_ms(
        started_at: float,
    ) -> float:
        """Return elapsed execution time in milliseconds."""

        return max(
            (perf_counter() - started_at) * 1_000,
            0.0,
        )
