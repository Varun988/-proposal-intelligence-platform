import json
from time import perf_counter
from typing import Any

from pydantic import ValidationError

from app.agents.risk_report.instructions import (
    RISK_REPORT_INSTRUCTION_VERSION,
    RISK_REPORT_SYSTEM_INSTRUCTIONS,
)
from app.agents.risk_report.policies import (
    RISK_REPORT_AGENT_NAME,
    RISK_REPORT_DECISION_DISCLAIMER,
)
from app.agents.risk_report.schemas import (
    RiskReportExecution,
    RiskReportInput,
    RiskReportResult,
)
from app.core.exceptions import AgentOutputValidationError
from app.schemas.llm import (
    LLMMessage,
    LLMRequest,
    MessageRole,
)
from app.services.llm_service import LLMService


class RiskReportAgent:
    """Synthesize validated findings into risk reports."""

    def __init__(
        self,
        llm_service: LLMService,
    ) -> None:
        self._llm_service = llm_service

    @property
    def name(self) -> str:
        """Return the unique agent name."""

        return RISK_REPORT_AGENT_NAME

    @property
    def instruction_version(self) -> str:
        """Return the active instruction version."""

        return RISK_REPORT_INSTRUCTION_VERSION

    async def generate_report(
        self,
        risk_input: RiskReportInput,
    ) -> RiskReportExecution:
        """Generate evidence-grounded risk and report output."""

        started_at = perf_counter()

        llm_request = self._build_llm_request(
            risk_input,
        )

        llm_response = await self._llm_service.generate(
            assessment_id=risk_input.assessment_id,
            request=llm_request,
        )

        result = self._validate_llm_output(
            structured_data=llm_response.structured_data,
            risk_input=risk_input,
        )

        result = self._canonicalize_result(
            result=result,
            risk_input=risk_input,
        )

        self._validate_source_finding_references(
            result=result,
            risk_input=risk_input,
        )

        return RiskReportExecution(
            result=result,
            source_proposal_finding_ids=[
                finding.finding_id for finding in risk_input.proposal_analysis.findings
            ],
            source_vendor_finding_ids=(
                [finding.finding_id for finding in risk_input.vendor_research.findings]
                if risk_input.vendor_research is not None
                else []
            ),
            llm_provider=llm_response.provider,
            llm_model=llm_response.model,
            instruction_version=self.instruction_version,
            total_execution_time_ms=self._elapsed_ms(
                started_at,
            ),
        )

    @staticmethod
    def _build_llm_request(
        risk_input: RiskReportInput,
    ) -> LLMRequest:
        """Build a structured risk-report request."""

        user_payload = {
            "task": (
                "Synthesize the validated specialist outputs into "
                "evidence-grounded risks, mitigations, clarification "
                "questions, a reviewer report, and an executive "
                "decision-support report."
            ),
            "risk_report_input": risk_input.model_dump(
                mode="json",
            ),
            "output_requirements": {
                "use_only_supplied_specialist_outputs": True,
                "preserve_source_finding_ids": True,
                "do_not_calculate_official_scores": True,
                "do_not_modify_deterministic_scores": True,
                "official_decision_prohibited": True,
                "human_review_required": True,
                "required_decision_disclaimer": (RISK_REPORT_DECISION_DISCLAIMER),
            },
        }

        return LLMRequest(
            messages=[
                LLMMessage(
                    role=MessageRole.SYSTEM,
                    content=RISK_REPORT_SYSTEM_INSTRUCTIONS,
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
            response_schema=(RiskReportResult.model_json_schema()),
            metadata={
                "agent_name": RISK_REPORT_AGENT_NAME,
                "instruction_version": (RISK_REPORT_INSTRUCTION_VERSION),
                "assessment_id": risk_input.assessment_id,
                "proposal_document_id": (risk_input.proposal_document_id),
                "vendor_name": risk_input.vendor_name,
            },
        )

    @staticmethod
    def _validate_llm_output(
        structured_data: dict[str, Any] | None,
        risk_input: RiskReportInput,
    ) -> RiskReportResult:
        """Validate structured output and execution identity."""

        if structured_data is None:
            raise AgentOutputValidationError(
                "Risk and Report Agent received no structured LLM output."
            )

        try:
            result = RiskReportResult.model_validate(
                structured_data,
            )
        except ValidationError as error:
            raise AgentOutputValidationError(
                "Risk and Report Agent returned invalid structured output."
            ) from error

        if result.assessment_id != risk_input.assessment_id:
            raise AgentOutputValidationError(
                "Risk report assessment ID does not match the requested assessment."
            )

        if result.proposal_document_id != risk_input.proposal_document_id:
            raise AgentOutputValidationError(
                "Risk report proposal document ID does not match the requested document."
            )

        if result.vendor_name.casefold() != risk_input.vendor_name.casefold():
            raise AgentOutputValidationError(
                "Risk report vendor name does not match the requested vendor."
            )

        return result

    @staticmethod
    def _normalize_source_agent(
        source_agent: str,
    ) -> str:
        """Normalize recognized specialist-agent aliases."""

        normalized_value = (
            source_agent.strip()
            .casefold()
            .replace("_", "-")
            .replace(" ", "-")
        )

        while "--" in normalized_value:
            normalized_value = normalized_value.replace(
                "--",
                "-",
            )

        source_agent_aliases = {
            "proposal-analysis": "proposal-analysis",
            "proposal-analysis-agent": "proposal-analysis",
            "vendor-research": "vendor-research",
            "vendor-research-agent": "vendor-research",
        }

        return source_agent_aliases.get(
            normalized_value,
            source_agent,
        )

    @staticmethod
    def _canonicalize_result(
        result: RiskReportResult,
        risk_input: RiskReportInput,
    ) -> RiskReportResult:
        """Replace governed output fields with trusted source data."""

        canonical_result = result.model_copy(
            deep=True,
        )

        canonical_result.executive_report.decision_disclaimer = RISK_REPORT_DECISION_DISCLAIMER

        proposal_findings = {
            finding.finding_id: finding for finding in risk_input.proposal_analysis.findings
        }

        vendor_findings = (
            {finding.finding_id: finding for finding in risk_input.vendor_research.findings}
            if risk_input.vendor_research is not None
            else {}
        )

        deterministic_scores = {
            score.rule_version: score for score in risk_input.deterministic_scores
        }

        source_agent_aliases = {
            "proposal-analysis": "proposal-analysis",
            "proposal_analysis": "proposal-analysis",
            "proposal analysis": "proposal-analysis",
            "vendor-research": "vendor-research",
            "vendor_research": "vendor-research",
            "vendor research": "vendor-research",
        }

        for risk in canonical_result.risks:
            canonical_evidence = []

            for evidence in risk.evidence:
                canonical_reference = evidence.model_copy(
                    deep=True,
                )

                normalized_source_agent = canonical_reference.source_agent.strip().casefold()

                canonical_source_agent = source_agent_aliases.get(
                    normalized_source_agent,
                )

                if canonical_source_agent is not None:
                    canonical_reference.source_agent = canonical_source_agent

                if canonical_reference.source_agent == "proposal-analysis":
                    source_finding = proposal_findings.get(
                        canonical_reference.source_finding_id,
                    )

                    if source_finding is None:
                        canonical_evidence.append(
                            canonical_reference,
                        )
                        continue

                    cited_chunk_id = (
                        canonical_reference.proposal_evidence.chunk_id
                        if (canonical_reference.proposal_evidence is not None)
                        else None
                    )

                    source_evidence = next(
                        (
                            item
                            for item in source_finding.evidence
                            if item.chunk_id == cited_chunk_id
                        ),
                        None,
                    )

                    if source_evidence is None:
                        canonical_evidence.append(
                            canonical_reference,
                        )
                        continue

                    canonical_reference.proposal_evidence = source_evidence.model_copy(
                        deep=True,
                    )
                    canonical_reference.vendor_evidence = None

                    canonical_evidence.append(
                        canonical_reference,
                    )
                    continue

                if canonical_reference.source_agent == "vendor-research":
                    source_finding = vendor_findings.get(
                        canonical_reference.source_finding_id,
                    )

                    if source_finding is None:
                        canonical_evidence.append(
                            canonical_reference,
                        )
                        continue

                    cited_evidence_id = (
                        canonical_reference.vendor_evidence.evidence_id
                        if (canonical_reference.vendor_evidence is not None)
                        else None
                    )

                    cited_chunk_id = (
                        canonical_reference.vendor_evidence.chunk_id
                        if (canonical_reference.vendor_evidence is not None)
                        else None
                    )

                    source_evidence = next(
                        (
                            item
                            for item in source_finding.evidence
                            if (
                                item.evidence_id == cited_evidence_id
                                or item.chunk_id == cited_chunk_id
                            )
                        ),
                        None,
                    )

                    if source_evidence is None:
                        canonical_evidence.append(
                            canonical_reference,
                        )
                        continue

                    canonical_reference.vendor_evidence = source_evidence.model_copy(
                        deep=True,
                    )
                    canonical_reference.proposal_evidence = None

                    canonical_evidence.append(
                        canonical_reference,
                    )
                    continue

                # Unknown source-agent values are intentionally
                # preserved so deterministic validation rejects them.
                canonical_evidence.append(
                    canonical_reference,
                )

            risk.evidence = canonical_evidence

            if risk.deterministic_score is not None:
                trusted_score = deterministic_scores.get(
                    risk.deterministic_score.rule_version,
                )

                if trusted_score is not None:
                    risk.deterministic_score = trusted_score.model_copy(
                        deep=True,
                    )

        return canonical_result

    @staticmethod
    def _validate_source_finding_references(
        result: RiskReportResult,
        risk_input: RiskReportInput,
    ) -> None:
        """Ensure risks reference supplied specialist findings."""

        proposal_finding_ids = {
            finding.finding_id for finding in risk_input.proposal_analysis.findings
        }

        vendor_finding_ids = (
            {finding.finding_id for finding in risk_input.vendor_research.findings}
            if risk_input.vendor_research is not None
            else set()
        )

        for risk in result.risks:
            for evidence in risk.evidence:
                if evidence.source_agent == "proposal-analysis":
                    if evidence.source_finding_id not in proposal_finding_ids:
                        raise AgentOutputValidationError(
                            "Risk report references an unknown Proposal Analysis finding."
                        )

                    if evidence.proposal_evidence is None:
                        raise AgentOutputValidationError(
                            "Proposal Analysis evidence reference is missing proposal evidence."
                        )

                elif evidence.source_agent == "vendor-research":
                    if evidence.source_finding_id not in vendor_finding_ids:
                        raise AgentOutputValidationError(
                            "Risk report references an unknown Vendor Research finding."
                        )

                    if evidence.vendor_evidence is None:
                        raise AgentOutputValidationError(
                            "Vendor Research evidence reference is missing vendor evidence."
                        )

                else:
                    raise AgentOutputValidationError(
                        "Risk report references an unauthorized source agent."
                    )

    @staticmethod
    def _elapsed_ms(
        started_at: float,
    ) -> float:
        """Return elapsed execution time in milliseconds."""

        return max(
            (perf_counter() - started_at) * 1_000,
            0.0,
        )
