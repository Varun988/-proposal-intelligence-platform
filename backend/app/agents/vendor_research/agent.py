import json
from datetime import UTC, date, datetime
from time import perf_counter
from typing import Any

from pydantic import ValidationError

from app.agents.vendor_research.instructions import (
    VENDOR_RESEARCH_INSTRUCTION_VERSION,
    VENDOR_RESEARCH_SYSTEM_INSTRUCTIONS,
)
from app.agents.vendor_research.policies import (
    VENDOR_RESEARCH_AGENT_NAME,
    VENDOR_RESEARCH_ALLOWED_SOURCE_TYPES,
    VENDOR_RESEARCH_ALLOWED_TOOLS,
    VENDOR_RESEARCH_MAX_TOOL_CALLS,
)
from app.agents.vendor_research.schemas import (
    VendorEvidenceCategory,
    VendorEvidenceFreshness,
    VendorEvidenceReference,
    VendorEvidenceSourceType,
    VendorResearchExecution,
    VendorResearchInput,
    VendorResearchResult,
    VendorResearchToolCallTrace,
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


class VendorResearchAgent:
    """Analyze approved vendor evidence through bounded tools."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        llm_service: LLMService,
        max_tool_calls: int = VENDOR_RESEARCH_MAX_TOOL_CALLS,
        current_date: date | None = None,
    ) -> None:
        if max_tool_calls < 1:
            raise AgentConfigurationError(
                "Vendor Research Agent must allow at least one tool call."
            )

        self._tool_registry = tool_registry
        self._llm_service = llm_service
        self._max_tool_calls = max_tool_calls
        self._current_date = current_date or datetime.now(UTC).date()

        self._validate_required_tools()

    @property
    def name(self) -> str:
        """Return the unique agent name."""

        return VENDOR_RESEARCH_AGENT_NAME

    @property
    def instruction_version(self) -> str:
        """Return the active instruction version."""

        return VENDOR_RESEARCH_INSTRUCTION_VERSION

    @property
    def max_tool_calls(self) -> int:
        """Return the maximum permitted tool calls."""

        return self._max_tool_calls

    async def research(
        self,
        research_input: VendorResearchInput,
    ) -> VendorResearchExecution:
        """Run evidence-grounded vendor research."""

        started_at = perf_counter()

        objectives = self._build_search_objectives(
            research_input,
        )

        if len(objectives) > self._max_tool_calls:
            raise AgentToolLimitError(
                "Vendor research requires more tool calls than "
                f"the configured limit. Required: {len(objectives)}. "
                f"Allowed: {self._max_tool_calls}."
            )

        tool_traces: list[VendorResearchToolCallTrace] = []
        retrieved_candidates: list[dict[str, Any]] = []

        for objective in objectives:
            tool_result = self._tool_registry.execute(
                tool_name="search_evidence",
                payload={
                    "query": objective,
                },
                agent_name=self.name,
                metadata={
                    "assessment_id": (research_input.assessment_id),
                    "vendor_name": research_input.vendor_name,
                },
            )

            response = self._extract_retrieval_response(
                tool_result.output,
            )

            candidates = response.get(
                "candidates",
                [],
            )

            if not isinstance(candidates, list):
                raise AgentOutputValidationError(
                    "Vendor evidence search returned an invalid candidate collection."
                )

            retrieved_candidates.extend(candidates)

            tool_traces.append(
                VendorResearchToolCallTrace(
                    tool_name="search_evidence",
                    query=objective,
                    succeeded=tool_result.succeeded,
                    execution_time_ms=(tool_result.execution_time_ms),
                    result_count=len(candidates),
                )
            )

        evidence_inventory = self._build_evidence_inventory(
            retrieved_candidates=retrieved_candidates,
            research_input=research_input,
        )

        llm_request = self._build_llm_request(
            research_input=research_input,
            evidence_inventory=evidence_inventory,
        )

        llm_response = await self._llm_service.generate(
            assessment_id=research_input.assessment_id,
            request=llm_request,
        )

        result = self._validate_llm_output(
            structured_data=llm_response.structured_data,
            research_input=research_input,
        )

        result = self._canonicalize_result_evidence(
            result=result,
            evidence_inventory=evidence_inventory,
        )

        return VendorResearchExecution(
            result=result,
            retrieved_evidence=evidence_inventory,
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
                f"Vendor Research Agent is missing required tools: {missing_text}."
            )

        unauthorized_tools = available_tool_names - set(VENDOR_RESEARCH_ALLOWED_TOOLS)

        if unauthorized_tools:
            unauthorized_text = ", ".join(sorted(unauthorized_tools))

            raise AgentConfigurationError(
                f"Vendor Research Agent received tools outside its allowlist: {unauthorized_text}."
            )

    @staticmethod
    def _build_search_objectives(
        research_input: VendorResearchInput,
    ) -> list:
        """Build focused vendor-evidence search queries."""

        return [
            (f"Find approved evidence about {objective} for vendor {research_input.vendor_name}.")
            for objective in research_input.research_objectives
        ]

    @staticmethod
    def _extract_retrieval_response(
        output: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Extract a retrieval response from tool output."""

        if output is None:
            raise AgentOutputValidationError("Vendor evidence search returned no output.")

        response = output.get("response")

        if not isinstance(response, dict):
            raise AgentOutputValidationError("Vendor evidence search returned an invalid response.")

        return response

    def _build_evidence_inventory(
        self,
        retrieved_candidates: list[dict[str, Any]],
        research_input: VendorResearchInput,
    ) -> list:
        """Create a unique, approved vendor-evidence inventory."""

        evidence_by_chunk_id: dict[
            str,
            VendorEvidenceReference,
        ] = {}

        allowed_source_types = {
            source_type.value for source_type in research_input.allowed_source_types
        }

        policy_source_types = set(VENDOR_RESEARCH_ALLOWED_SOURCE_TYPES)

        permitted_source_types = allowed_source_types & policy_source_types

        for candidate in retrieved_candidates:
            evidence = self._candidate_to_evidence(
                candidate=candidate,
                stale_after_days=(research_input.stale_after_days),
            )

            if evidence is None:
                continue

            if evidence.source_type.value not in (permitted_source_types):
                continue

            evidence_by_chunk_id[evidence.chunk_id] = evidence

        return list(evidence_by_chunk_id.values())

    def _candidate_to_evidence(
        self,
        candidate: dict[str, Any],
        stale_after_days: int,
    ) -> VendorEvidenceReference | None:
        """Convert one retrieval candidate to vendor evidence."""

        chunk = candidate.get("chunk")

        if not isinstance(chunk, dict):
            return None

        citation = chunk.get("citation")
        metadata = chunk.get("metadata", {})

        if not isinstance(citation, dict):
            return None

        if not isinstance(metadata, dict):
            metadata = {}

        chunk_id = chunk.get("chunk_id")
        document_id = chunk.get("document_id")
        text = chunk.get("text")
        file_name = citation.get("file_name")
        page_number = citation.get("page_number")
        citation_label = candidate.get("citation_label")

        source_type_value = metadata.get(
            "source_type",
            VendorEvidenceSourceType.PROVIDED_DOCUMENT.value,
        )
        category_value = metadata.get(
            "evidence_category",
            VendorEvidenceCategory.COMPANY_PROFILE.value,
        )
        source_name = metadata.get(
            "source_name",
            file_name,
        )

        if not all(
            [
                isinstance(chunk_id, str),
                isinstance(document_id, str),
                isinstance(text, str),
                isinstance(file_name, str),
                isinstance(page_number, int),
                isinstance(citation_label, str),
                isinstance(source_type_value, str),
                isinstance(category_value, str),
                isinstance(source_name, str),
            ]
        ):
            return None

        try:
            source_type = VendorEvidenceSourceType(source_type_value)
            category = VendorEvidenceCategory(category_value)
        except ValueError:
            return None

        publication_date = self._parse_date(metadata.get("publication_date"))
        retrieved_date = self._parse_date(metadata.get("retrieved_date"))

        freshness = self._classify_freshness(
            publication_date=publication_date,
            retrieved_date=retrieved_date,
            stale_after_days=stale_after_days,
        )

        return VendorEvidenceReference(
            evidence_id=f"evidence-{chunk_id}",
            chunk_id=chunk_id,
            document_id=document_id,
            file_name=file_name,
            page_number=page_number,
            citation_label=citation_label,
            supporting_text=text,
            category=category,
            source_type=source_type,
            source_name=source_name,
            publication_date=publication_date,
            retrieved_date=retrieved_date,
            freshness=freshness,
            retrieval_score=candidate.get("retrieval_score"),
            final_score=candidate.get("final_score"),
            metadata={
                key: value
                for key, value in metadata.items()
                if isinstance(
                    value,
                    (
                        str,
                        int,
                        float,
                        bool,
                        type(None),
                    ),
                )
            },
        )

    def _classify_freshness(
        self,
        publication_date: date | None,
        retrieved_date: date | None,
        stale_after_days: int,
    ) -> VendorEvidenceFreshness:
        """Classify evidence freshness from available dates."""

        reference_date = publication_date or retrieved_date

        if reference_date is None:
            return VendorEvidenceFreshness.UNKNOWN

        evidence_age = (self._current_date - reference_date).days

        if evidence_age < 0:
            return VendorEvidenceFreshness.UNKNOWN

        if evidence_age > stale_after_days:
            return VendorEvidenceFreshness.STALE

        return VendorEvidenceFreshness.CURRENT

    @staticmethod
    def _parse_date(
        value: object,
    ) -> date | None:
        """Parse an ISO date stored in retrieval metadata."""

        if isinstance(value, date):
            return value

        if not isinstance(value, str):
            return None

        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _build_llm_request(
        research_input: VendorResearchInput,
        evidence_inventory: list[VendorEvidenceReference],
    ) -> LLMRequest:
        """Build a structured Vendor Research Agent request."""

        user_payload = {
            "task": ("Research the vendor using only the supplied approved evidence."),
            "research_input": research_input.model_dump(
                mode="json",
            ),
            "approved_evidence": [
                evidence.model_dump(mode="json") for evidence in evidence_inventory
            ],
            "output_requirements": {
                "facts_must_have_citations": True,
                "distinguish_vendor_claims": True,
                "mark_stale_evidence": True,
                "approval_decision_prohibited": True,
                "human_review_required": True,
            },
        }

        return LLMRequest(
            messages=[
                LLMMessage(
                    role=MessageRole.SYSTEM,
                    content=(VENDOR_RESEARCH_SYSTEM_INSTRUCTIONS),
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
            response_schema=(VendorResearchResult.model_json_schema()),
            metadata={
                "agent_name": VENDOR_RESEARCH_AGENT_NAME,
                "instruction_version": (VENDOR_RESEARCH_INSTRUCTION_VERSION),
                "assessment_id": (research_input.assessment_id),
                "vendor_name": research_input.vendor_name,
            },
        )

    @staticmethod
    def _canonicalize_result_evidence(
        result: VendorResearchResult,
        evidence_inventory: list[VendorEvidenceReference],
    ) -> VendorResearchResult:
        """Replace LLM citation metadata with retrieved source data."""

        evidence_by_id = {evidence.evidence_id: evidence for evidence in evidence_inventory}

        evidence_by_chunk_id = {evidence.chunk_id: evidence for evidence in evidence_inventory}

        canonical_result = result.model_copy(
            deep=True,
        )

        for finding in canonical_result.findings:
            canonical_evidence: list[VendorEvidenceReference] = []

            for cited_evidence in finding.evidence:
                retrieved_evidence = evidence_by_id.get(
                    cited_evidence.evidence_id,
                )

                if retrieved_evidence is None:
                    retrieved_evidence = evidence_by_chunk_id.get(
                        cited_evidence.chunk_id,
                    )

                if retrieved_evidence is None:
                    canonical_evidence.append(
                        cited_evidence,
                    )
                    continue

                canonical_evidence.append(
                    retrieved_evidence.model_copy(
                        deep=True,
                    )
                )

            finding.evidence = canonical_evidence

        for conflict in canonical_result.conflicts:
            first_retrieved = evidence_by_id.get(
                conflict.first_evidence.evidence_id,
            )

            if first_retrieved is None:
                first_retrieved = evidence_by_chunk_id.get(
                    conflict.first_evidence.chunk_id,
                )

            if first_retrieved is not None:
                conflict.first_evidence = first_retrieved.model_copy(
                    deep=True,
                )

            second_retrieved = evidence_by_id.get(
                conflict.second_evidence.evidence_id,
            )

            if second_retrieved is None:
                second_retrieved = evidence_by_chunk_id.get(
                    conflict.second_evidence.chunk_id,
                )

            if second_retrieved is not None:
                conflict.second_evidence = second_retrieved.model_copy(
                    deep=True,
                )

        canonical_result.stale_evidence_ids = [
            evidence.evidence_id
            for evidence in evidence_inventory
            if (evidence.freshness is VendorEvidenceFreshness.STALE)
        ]

        return canonical_result

    @staticmethod
    def _validate_llm_output(
        structured_data: dict[str, Any] | None,
        research_input: VendorResearchInput,
    ) -> VendorResearchResult:
        """Validate structured output and execution identity."""

        if structured_data is None:
            raise AgentOutputValidationError(
                "Vendor Research Agent received no structured LLM output."
            )

        try:
            result = VendorResearchResult.model_validate(
                structured_data,
            )
        except ValidationError as error:
            raise AgentOutputValidationError(
                "Vendor Research Agent returned invalid structured output."
            ) from error

        if result.assessment_id != research_input.assessment_id:
            raise AgentOutputValidationError(
                "Vendor research assessment ID does not match the requested assessment."
            )

        if result.vendor_name.casefold() != research_input.vendor_name.casefold():
            raise AgentOutputValidationError(
                "Vendor research output vendor name does not match the requested vendor."
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
