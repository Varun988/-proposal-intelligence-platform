from app.agents.vendor_research.instructions import (
    VENDOR_RESEARCH_INSTRUCTION_VERSION,
)
from app.agents.vendor_research.policies import (
    VENDOR_RESEARCH_ALLOWED_SOURCE_TYPES,
    VENDOR_RESEARCH_ALLOWED_TOOLS,
    VENDOR_RESEARCH_MAX_TOOL_CALLS,
)
from app.agents.vendor_research.schemas import (
    VendorResearchExecution,
    VendorResearchToolCallTrace,
)
from app.evaluation.evaluators.base import BaseEvaluator
from app.evaluation.schemas import (
    EvaluationFinding,
    EvaluationResult,
    EvaluationSeverity,
    EvaluationStatus,
)


class VendorResearchTrajectoryEvaluator(
    BaseEvaluator[VendorResearchExecution],
):
    """Evaluate the Vendor Research Agent execution trajectory."""

    def __init__(
        self,
        maximum_tool_calls: int = (VENDOR_RESEARCH_MAX_TOOL_CALLS),
    ) -> None:
        if maximum_tool_calls < 1:
            raise ValueError("maximum_tool_calls must be at least 1.")

        self._maximum_tool_calls = maximum_tool_calls

    @property
    def name(self) -> str:
        """Return the evaluator name."""

        return "vendor-research-trajectory-evaluator"

    @property
    def version(self) -> str:
        """Return the evaluator version."""

        return "1.0.0"

    def evaluate(
        self,
        target: VendorResearchExecution,
    ) -> EvaluationResult:
        """Evaluate tool use, limits, sources, and governance."""

        findings: list[EvaluationFinding] = []

        self._evaluate_tool_count(
            target=target,
            findings=findings,
        )
        self._evaluate_instruction_version(
            target=target,
            findings=findings,
        )
        self._evaluate_human_review(
            target=target,
            findings=findings,
        )
        self._evaluate_tool_calls(
            tool_calls=target.tool_calls,
            findings=findings,
        )
        self._evaluate_retrieved_source_types(
            target=target,
            findings=findings,
        )

        required_tool_used = any(
            trace.tool_name == "search_evidence" for trace in target.tool_calls
        )

        if not required_tool_used:
            findings.append(
                EvaluationFinding(
                    finding_id=("vendor-required-tool-not-used"),
                    description=(
                        "The Vendor Research Agent did not use the required search_evidence tool."
                    ),
                    severity=EvaluationSeverity.CRITICAL,
                    location="tool_calls",
                    related_ids=[
                        "search_evidence",
                    ],
                )
            )

        successful_tool_calls = sum(1 for trace in target.tool_calls if trace.succeeded)

        failed_tool_calls = len(target.tool_calls) - successful_tool_calls

        result_bearing_tool_calls = sum(1 for trace in target.tool_calls if trace.result_count > 0)

        critical_count = sum(
            1 for finding in findings if finding.severity is EvaluationSeverity.CRITICAL
        )

        high_count = sum(1 for finding in findings if finding.severity is EvaluationSeverity.HIGH)

        warning_count = sum(
            1
            for finding in findings
            if finding.severity
            in {
                EvaluationSeverity.LOW,
                EvaluationSeverity.MEDIUM,
            }
        )

        score = self._calculate_score(
            critical_count=critical_count,
            high_count=high_count,
            warning_count=warning_count,
        )

        if critical_count > 0 or high_count > 0:
            status = EvaluationStatus.FAILED
            summary = (
                "The Vendor Research Agent trajectory violated "
                "one or more required execution controls."
            )
        elif warning_count > 0:
            status = EvaluationStatus.WARNING
            summary = "The Vendor Research Agent trajectory completed with non-blocking warnings."
        else:
            status = EvaluationStatus.PASSED
            summary = (
                "The Vendor Research Agent trajectory passed all deterministic execution checks."
            )

        return EvaluationResult(
            evaluator_name=self.name,
            evaluator_version=self.version,
            status=status,
            score=score,
            summary=summary,
            findings=findings,
            metrics={
                "declared_tool_call_count": (target.tool_call_count),
                "trace_tool_call_count": len(target.tool_calls),
                "maximum_tool_calls": (self._maximum_tool_calls),
                "successful_tool_calls": (successful_tool_calls),
                "failed_tool_calls": failed_tool_calls,
                "result_bearing_tool_calls": (result_bearing_tool_calls),
                "required_tool_used": required_tool_used,
                "retrieved_evidence_count": len(target.retrieved_evidence),
                "human_review_required": (target.result.human_review_required),
                "instruction_version_matches": (
                    target.instruction_version == VENDOR_RESEARCH_INSTRUCTION_VERSION
                ),
            },
        )

    def _evaluate_tool_count(
        self,
        target: VendorResearchExecution,
        findings: list[EvaluationFinding],
    ) -> None:
        """Validate declared, traced, and permitted tool counts."""

        trace_count = len(target.tool_calls)

        if target.tool_call_count != trace_count:
            findings.append(
                EvaluationFinding(
                    finding_id=("vendor-tool-call-count-mismatch"),
                    description=(
                        "The declared Vendor Research tool-call count does not match the trace."
                    ),
                    severity=EvaluationSeverity.CRITICAL,
                    location="tool_call_count",
                    metadata={
                        "declared_count": (target.tool_call_count),
                        "trace_count": trace_count,
                    },
                )
            )

        if target.tool_call_count > self._maximum_tool_calls:
            findings.append(
                EvaluationFinding(
                    finding_id=("vendor-tool-call-limit-exceeded"),
                    description=(
                        "The Vendor Research Agent exceeded the configured maximum tool-call count."
                    ),
                    severity=EvaluationSeverity.CRITICAL,
                    location="tool_call_count",
                    metadata={
                        "actual_count": (target.tool_call_count),
                        "maximum_count": (self._maximum_tool_calls),
                    },
                )
            )

    @staticmethod
    def _evaluate_instruction_version(
        target: VendorResearchExecution,
        findings: list[EvaluationFinding],
    ) -> None:
        """Validate the Vendor Research instruction version."""

        if target.instruction_version != VENDOR_RESEARCH_INSTRUCTION_VERSION:
            findings.append(
                EvaluationFinding(
                    finding_id=("vendor-instruction-version-mismatch"),
                    description=(
                        "The Vendor Research execution used an unexpected instruction version."
                    ),
                    severity=EvaluationSeverity.HIGH,
                    location="instruction_version",
                    metadata={
                        "actual_version": (target.instruction_version),
                        "expected_version": (VENDOR_RESEARCH_INSTRUCTION_VERSION),
                    },
                )
            )

    @staticmethod
    def _evaluate_human_review(
        target: VendorResearchExecution,
        findings: list[EvaluationFinding],
    ) -> None:
        """Ensure vendor research remains human reviewed."""

        if not target.result.human_review_required:
            findings.append(
                EvaluationFinding(
                    finding_id=("vendor-human-review-disabled"),
                    description=("The Vendor Research Agent output does not require human review."),
                    severity=EvaluationSeverity.CRITICAL,
                    location=("result.human_review_required"),
                )
            )

        for finding_index, vendor_finding in enumerate(target.result.findings):
            if vendor_finding.human_review_required:
                continue

            findings.append(
                EvaluationFinding(
                    finding_id=(
                        f"vendor-finding-human-review-disabled-{vendor_finding.finding_id}"
                    ),
                    description=("An individual vendor finding does not require human review."),
                    severity=EvaluationSeverity.HIGH,
                    location=(f"result.findings[{finding_index}].human_review_required"),
                    related_ids=[
                        vendor_finding.finding_id,
                    ],
                )
            )

    @staticmethod
    def _evaluate_tool_calls(
        tool_calls: list[VendorResearchToolCallTrace],
        findings: list[EvaluationFinding],
    ) -> None:
        """Validate each Vendor Research tool call."""

        allowed_tools = set(VENDOR_RESEARCH_ALLOWED_TOOLS)

        for trace_index, trace in enumerate(tool_calls):
            location = f"tool_calls[{trace_index}]"

            if trace.tool_name not in allowed_tools:
                findings.append(
                    EvaluationFinding(
                        finding_id=(f"vendor-unauthorized-tool-{trace_index}"),
                        description=(
                            "The Vendor Research Agent called a "
                            "tool outside its approved allowlist."
                        ),
                        severity=EvaluationSeverity.CRITICAL,
                        location=location,
                        related_ids=[
                            trace.tool_name,
                        ],
                    )
                )

            if not trace.succeeded:
                findings.append(
                    EvaluationFinding(
                        finding_id=(f"vendor-failed-tool-call-{trace_index}"),
                        description=("A Vendor Research tool call did not complete successfully."),
                        severity=EvaluationSeverity.HIGH,
                        location=location,
                        related_ids=[
                            trace.tool_name,
                        ],
                        metadata={
                            "error_message": (trace.error_message),
                        },
                    )
                )

            if trace.tool_name == "search_evidence" and (
                trace.query is None or not trace.query.strip()
            ):
                findings.append(
                    EvaluationFinding(
                        finding_id=(f"vendor-missing-search-query-{trace_index}"),
                        description=(
                            "A vendor search_evidence call does not contain a valid query."
                        ),
                        severity=EvaluationSeverity.HIGH,
                        location=f"{location}.query",
                    )
                )

            if trace.tool_name == "search_evidence" and trace.succeeded and trace.result_count == 0:
                findings.append(
                    EvaluationFinding(
                        finding_id=(f"vendor-empty-search-result-{trace_index}"),
                        description=(
                            "A successful vendor evidence search returned no evidence candidates."
                        ),
                        severity=EvaluationSeverity.MEDIUM,
                        location=location,
                        related_ids=[
                            trace.tool_name,
                        ],
                    )
                )

    @staticmethod
    def _evaluate_retrieved_source_types(
        target: VendorResearchExecution,
        findings: list[EvaluationFinding],
    ) -> None:
        """Ensure retrieved evidence uses approved source types."""

        allowed_source_types = set(VENDOR_RESEARCH_ALLOWED_SOURCE_TYPES)

        for evidence_index, evidence in enumerate(target.retrieved_evidence):
            if evidence.source_type.value in allowed_source_types:
                continue

            findings.append(
                EvaluationFinding(
                    finding_id=(f"vendor-unapproved-retrieved-source-{evidence.evidence_id}"),
                    description=(
                        "Retrieved vendor evidence uses a source type outside the approved policy."
                    ),
                    severity=EvaluationSeverity.CRITICAL,
                    location=(f"retrieved_evidence[{evidence_index}]"),
                    related_ids=[
                        evidence.evidence_id,
                    ],
                    metadata={
                        "source_type": (evidence.source_type.value),
                    },
                )
            )

    @staticmethod
    def _calculate_score(
        critical_count: int,
        high_count: int,
        warning_count: int,
    ) -> float:
        """Calculate a bounded trajectory score."""

        penalty = critical_count * 0.5 + high_count * 0.25 + warning_count * 0.1

        return max(
            1.0 - penalty,
            0.0,
        )
