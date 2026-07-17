from app.agents.proposal_analysis.instructions import (
    PROPOSAL_ANALYSIS_INSTRUCTION_VERSION,
)
from app.agents.proposal_analysis.policies import (
    PROPOSAL_ANALYSIS_ALLOWED_TOOLS,
    PROPOSAL_ANALYSIS_MAX_TOOL_CALLS,
)
from app.agents.proposal_analysis.schemas import (
    AgentToolCallTrace,
    ProposalAnalysisExecution,
)
from app.evaluation.evaluators.base import BaseEvaluator
from app.evaluation.schemas import (
    EvaluationFinding,
    EvaluationResult,
    EvaluationSeverity,
    EvaluationStatus,
)


class ProposalTrajectoryEvaluator(
    BaseEvaluator[ProposalAnalysisExecution],
):
    """Evaluate the Proposal Analysis Agent execution trajectory."""

    def __init__(
        self,
        maximum_tool_calls: int = (PROPOSAL_ANALYSIS_MAX_TOOL_CALLS),
    ) -> None:
        if maximum_tool_calls < 1:
            raise ValueError("maximum_tool_calls must be at least 1.")

        self._maximum_tool_calls = maximum_tool_calls

    @property
    def name(self) -> str:
        """Return the evaluator name."""

        return "proposal-trajectory-evaluator"

    @property
    def version(self) -> str:
        """Return the evaluator version."""

        return "1.0.0"

    def evaluate(
        self,
        target: ProposalAnalysisExecution,
    ) -> EvaluationResult:
        """Evaluate tool use, limits, identity, and governance."""

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

        required_tool_used = any(
            trace.tool_name == "search_evidence" for trace in target.tool_calls
        )

        if not required_tool_used:
            findings.append(
                EvaluationFinding(
                    finding_id="required-tool-not-used",
                    description=(
                        "The Proposal Analysis Agent did not use the required search_evidence tool."
                    ),
                    severity=EvaluationSeverity.CRITICAL,
                    location="tool_calls",
                    related_ids=[
                        "search_evidence",
                    ],
                )
            )

        critical_findings = [
            finding for finding in findings if finding.severity is EvaluationSeverity.CRITICAL
        ]

        high_findings = [
            finding for finding in findings if finding.severity is EvaluationSeverity.HIGH
        ]

        warning_findings = [
            finding
            for finding in findings
            if finding.severity
            in {
                EvaluationSeverity.LOW,
                EvaluationSeverity.MEDIUM,
            }
        ]

        score = self._calculate_score(
            critical_count=len(critical_findings),
            high_count=len(high_findings),
            warning_count=len(warning_findings),
        )

        if critical_findings or high_findings:
            status = EvaluationStatus.FAILED
            summary = (
                "The Proposal Analysis Agent trajectory violated "
                "one or more required execution controls."
            )
        elif warning_findings:
            status = EvaluationStatus.WARNING
            summary = "The Proposal Analysis Agent trajectory completed with non-blocking warnings."
        else:
            status = EvaluationStatus.PASSED
            summary = (
                "The Proposal Analysis Agent trajectory passed all deterministic execution checks."
            )

        successful_tool_calls = sum(1 for trace in target.tool_calls if trace.succeeded)

        failed_tool_calls = len(target.tool_calls) - successful_tool_calls

        result_bearing_tool_calls = sum(1 for trace in target.tool_calls if trace.result_count > 0)

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
                "human_review_required": (target.result.human_review_required),
                "instruction_version_matches": (
                    target.instruction_version == PROPOSAL_ANALYSIS_INSTRUCTION_VERSION
                ),
            },
        )

    def _evaluate_tool_count(
        self,
        target: ProposalAnalysisExecution,
        findings: list[EvaluationFinding],
    ) -> None:
        """Validate declared, traced, and permitted tool-call counts."""

        trace_count = len(target.tool_calls)

        if target.tool_call_count != trace_count:
            findings.append(
                EvaluationFinding(
                    finding_id="tool-call-count-mismatch",
                    description=(
                        "The declared tool-call count does not match the execution trace."
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
                    finding_id="tool-call-limit-exceeded",
                    description=("The agent exceeded the configured maximum number of tool calls."),
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
        target: ProposalAnalysisExecution,
        findings: list[EvaluationFinding],
    ) -> None:
        """Validate the agent instruction version."""

        if target.instruction_version != PROPOSAL_ANALYSIS_INSTRUCTION_VERSION:
            findings.append(
                EvaluationFinding(
                    finding_id="instruction-version-mismatch",
                    description=("The agent execution used an unexpected instruction version."),
                    severity=EvaluationSeverity.HIGH,
                    location="instruction_version",
                    metadata={
                        "actual_version": (target.instruction_version),
                        "expected_version": (PROPOSAL_ANALYSIS_INSTRUCTION_VERSION),
                    },
                )
            )

    @staticmethod
    def _evaluate_human_review(
        target: ProposalAnalysisExecution,
        findings: list[EvaluationFinding],
    ) -> None:
        """Ensure the analysis remains subject to human review."""

        if not target.result.human_review_required:
            findings.append(
                EvaluationFinding(
                    finding_id="human-review-disabled",
                    description=(
                        "The Proposal Analysis Agent output does not require human review."
                    ),
                    severity=EvaluationSeverity.CRITICAL,
                    location=("result.human_review_required"),
                )
            )

        for finding_index, proposal_finding in enumerate(target.result.findings):
            if proposal_finding.human_review_required:
                continue

            findings.append(
                EvaluationFinding(
                    finding_id=(f"finding-human-review-disabled-{proposal_finding.finding_id}"),
                    description=("An individual proposal finding does not require human review."),
                    severity=EvaluationSeverity.HIGH,
                    location=(f"result.findings[{finding_index}].human_review_required"),
                    related_ids=[
                        proposal_finding.finding_id,
                    ],
                )
            )

    @staticmethod
    def _evaluate_tool_calls(
        tool_calls: list[AgentToolCallTrace],
        findings: list[EvaluationFinding],
    ) -> None:
        """Validate every recorded tool call."""

        allowed_tools = set(PROPOSAL_ANALYSIS_ALLOWED_TOOLS)

        for trace_index, trace in enumerate(tool_calls):
            location = f"tool_calls[{trace_index}]"

            if trace.tool_name not in allowed_tools:
                findings.append(
                    EvaluationFinding(
                        finding_id=(f"unauthorized-tool-{trace_index}"),
                        description=("The agent called a tool outside its approved allowlist."),
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
                        finding_id=(f"failed-tool-call-{trace_index}"),
                        description=(
                            "A tool call in the agent trajectory did not complete successfully."
                        ),
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
                        finding_id=(f"missing-search-query-{trace_index}"),
                        description=(
                            "A search_evidence call does not contain a valid search query."
                        ),
                        severity=EvaluationSeverity.HIGH,
                        location=f"{location}.query",
                    )
                )

            if trace.tool_name == "search_evidence" and trace.succeeded and trace.result_count == 0:
                findings.append(
                    EvaluationFinding(
                        finding_id=(f"empty-search-result-{trace_index}"),
                        description=(
                            "A successful evidence search returned no candidate evidence."
                        ),
                        severity=EvaluationSeverity.MEDIUM,
                        location=location,
                        related_ids=[
                            trace.tool_name,
                        ],
                    )
                )

    @staticmethod
    def _calculate_score(
        critical_count: int,
        high_count: int,
        warning_count: int,
    ) -> float:
        """Calculate a bounded deterministic trajectory score."""

        penalty = critical_count * 0.5 + high_count * 0.25 + warning_count * 0.1

        return max(
            1.0 - penalty,
            0.0,
        )
