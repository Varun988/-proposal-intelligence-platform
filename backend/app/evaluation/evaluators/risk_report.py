from app.agents.risk_report.instructions import (
    RISK_REPORT_INSTRUCTION_VERSION,
)
from app.agents.risk_report.policies import (
    RISK_REPORT_ALLOWED_SOURCE_AGENTS,
    RISK_REPORT_DECISION_DISCLAIMER,
)
from app.agents.risk_report.schemas import (
    RiskReportExecution,
)
from app.evaluation.evaluators.base import BaseEvaluator
from app.evaluation.schemas import (
    EvaluationFinding,
    EvaluationResult,
    EvaluationSeverity,
    EvaluationStatus,
)


class RiskReportEvaluator(
    BaseEvaluator[RiskReportExecution],
):
    """Evaluate Risk and Report Agent output and governance."""

    @property
    def name(self) -> str:
        """Return the evaluator name."""

        return "risk-report-evaluator"

    @property
    def version(self) -> str:
        """Return the evaluator version."""

        return "1.0.0"

    def evaluate(
        self,
        target: RiskReportExecution,
    ) -> EvaluationResult:
        """Evaluate source integrity, reports, and governance."""

        findings: list[EvaluationFinding] = []

        self._evaluate_instruction_version(
            target=target,
            findings=findings,
        )
        self._evaluate_governance(
            target=target,
            findings=findings,
        )
        self._evaluate_risks(
            target=target,
            findings=findings,
        )
        self._evaluate_report_references(
            target=target,
            findings=findings,
        )

        critical_count = sum(
            1
            for finding in findings
            if finding.severity
            is EvaluationSeverity.CRITICAL
        )

        high_count = sum(
            1
            for finding in findings
            if finding.severity
            is EvaluationSeverity.HIGH
        )

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

        if critical_count or high_count:
            status = EvaluationStatus.FAILED
            summary = (
                "The Risk and Report Agent output violated one or "
                "more evidence, governance, or report controls."
            )
        elif warning_count:
            status = EvaluationStatus.WARNING
            summary = (
                "The Risk and Report Agent output completed with "
                "non-blocking warnings."
            )
        else:
            status = EvaluationStatus.PASSED
            summary = (
                "The Risk and Report Agent output passed all "
                "deterministic validation controls."
            )

        referenced_proposal_findings = {
            evidence.source_finding_id
            for risk in target.result.risks
            for evidence in risk.evidence
            if evidence.source_agent == "proposal-analysis"
        }

        referenced_vendor_findings = {
            evidence.source_finding_id
            for risk in target.result.risks
            for evidence in risk.evidence
            if evidence.source_agent == "vendor-research"
        }

        return EvaluationResult(
            evaluator_name=self.name,
            evaluator_version=self.version,
            status=status,
            score=score,
            summary=summary,
            findings=findings,
            metrics={
                "risk_count": len(target.result.risks),
                "source_proposal_finding_count": len(
                    target.source_proposal_finding_ids
                ),
                "source_vendor_finding_count": len(
                    target.source_vendor_finding_ids
                ),
                "referenced_proposal_finding_count": len(
                    referenced_proposal_findings
                ),
                "referenced_vendor_finding_count": len(
                    referenced_vendor_findings
                ),
                "human_review_required": (
                    target.result.human_review_required
                ),
                "official_decision_provided": (
                    target.result.official_decision_provided
                ),
                "instruction_version_matches": (
                    target.instruction_version
                    == RISK_REPORT_INSTRUCTION_VERSION
                ),
            },
        )

    @staticmethod
    def _evaluate_instruction_version(
        target: RiskReportExecution,
        findings: list[EvaluationFinding],
    ) -> None:
        """Validate the agent instruction version."""

        if (
            target.instruction_version
            != RISK_REPORT_INSTRUCTION_VERSION
        ):
            findings.append(
                EvaluationFinding(
                    finding_id=(
                        "risk-report-instruction-version-mismatch"
                    ),
                    description=(
                        "The Risk and Report Agent used an "
                        "unexpected instruction version."
                    ),
                    severity=EvaluationSeverity.HIGH,
                    location="instruction_version",
                    metadata={
                        "actual_version": (
                            target.instruction_version
                        ),
                        "expected_version": (
                            RISK_REPORT_INSTRUCTION_VERSION
                        ),
                    },
                )
            )

    @staticmethod
    def _evaluate_governance(
        target: RiskReportExecution,
        findings: list[EvaluationFinding],
    ) -> None:
        """Validate human review and decision restrictions."""

        if not target.result.human_review_required:
            findings.append(
                EvaluationFinding(
                    finding_id="risk-report-human-review-disabled",
                    description=(
                        "The Risk and Report output does not "
                        "require human review."
                    ),
                    severity=EvaluationSeverity.CRITICAL,
                    location=(
                        "result.human_review_required"
                    ),
                )
            )

        if target.result.official_decision_provided:
            findings.append(
                EvaluationFinding(
                    finding_id=(
                        "risk-report-official-decision-provided"
                    ),
                    description=(
                        "The Risk and Report Agent produced an "
                        "official vendor decision."
                    ),
                    severity=EvaluationSeverity.CRITICAL,
                    location=(
                        "result.official_decision_provided"
                    ),
                )
            )

        if (
            target.result.executive_report.decision_disclaimer
            != RISK_REPORT_DECISION_DISCLAIMER
        ):
            findings.append(
                EvaluationFinding(
                    finding_id=(
                        "risk-report-disclaimer-mismatch"
                    ),
                    description=(
                        "The executive report does not contain "
                        "the required decision-support disclaimer."
                    ),
                    severity=EvaluationSeverity.CRITICAL,
                    location=(
                        "result.executive_report"
                        ".decision_disclaimer"
                    ),
                )
            )

    @staticmethod
    def _evaluate_risks(
        target: RiskReportExecution,
        findings: list[EvaluationFinding],
    ) -> None:
        """Validate risk sources, evidence, and scores."""

        allowed_source_agents = set(
            RISK_REPORT_ALLOWED_SOURCE_AGENTS
        )
        proposal_finding_ids = set(
            target.source_proposal_finding_ids
        )
        vendor_finding_ids = set(
            target.source_vendor_finding_ids
        )

        seen_risk_ids: set[str] = set()

        for risk_index, risk in enumerate(
            target.result.risks
        ):
            location = f"result.risks[{risk_index}]"

            if risk.risk_id in seen_risk_ids:
                findings.append(
                    EvaluationFinding(
                        finding_id=(
                            "duplicate-risk-id-"
                            f"{risk.risk_id}"
                        ),
                        description=(
                            "The Risk and Report output contains "
                            "a duplicate risk ID."
                        ),
                        severity=EvaluationSeverity.HIGH,
                        location=location,
                        related_ids=[risk.risk_id],
                    )
                )

            seen_risk_ids.add(risk.risk_id)

            if not risk.human_review_required:
                findings.append(
                    EvaluationFinding(
                        finding_id=(
                            "risk-human-review-disabled-"
                            f"{risk.risk_id}"
                        ),
                        description=(
                            "An individual synthesized risk does "
                            "not require human review."
                        ),
                        severity=EvaluationSeverity.HIGH,
                        location=(
                            f"{location}"
                            ".human_review_required"
                        ),
                        related_ids=[risk.risk_id],
                    )
                )

            for evidence_index, evidence in enumerate(
                risk.evidence
            ):
                evidence_location = (
                    f"{location}.evidence[{evidence_index}]"
                )

                if (
                    evidence.source_agent
                    not in allowed_source_agents
                ):
                    findings.append(
                        EvaluationFinding(
                            finding_id=(
                                "unauthorized-risk-source-agent-"
                                f"{risk.risk_id}-"
                                f"{evidence_index}"
                            ),
                            description=(
                                "Risk evidence references an "
                                "unauthorized source agent."
                            ),
                            severity=EvaluationSeverity.CRITICAL,
                            location=evidence_location,
                            related_ids=[
                                risk.risk_id,
                                evidence.source_agent,
                            ],
                        )
                    )
                    continue

                if evidence.source_agent == "proposal-analysis":
                    if (
                        evidence.source_finding_id
                        not in proposal_finding_ids
                    ):
                        findings.append(
                            EvaluationFinding(
                                finding_id=(
                                    "unknown-proposal-risk-source-"
                                    f"{risk.risk_id}-"
                                    f"{evidence.source_finding_id}"
                                ),
                                description=(
                                    "Risk evidence references an "
                                    "unknown Proposal Analysis "
                                    "finding."
                                ),
                                severity=(
                                    EvaluationSeverity.CRITICAL
                                ),
                                location=evidence_location,
                                related_ids=[
                                    risk.risk_id,
                                    evidence.source_finding_id,
                                ],
                            )
                        )

                    if evidence.proposal_evidence is None:
                        findings.append(
                            EvaluationFinding(
                                finding_id=(
                                    "missing-proposal-risk-evidence-"
                                    f"{risk.risk_id}-"
                                    f"{evidence_index}"
                                ),
                                description=(
                                    "Proposal Analysis source does "
                                    "not contain proposal evidence."
                                ),
                                severity=(
                                    EvaluationSeverity.CRITICAL
                                ),
                                location=evidence_location,
                            )
                        )

                if evidence.source_agent == "vendor-research":
                    if (
                        evidence.source_finding_id
                        not in vendor_finding_ids
                    ):
                        findings.append(
                            EvaluationFinding(
                                finding_id=(
                                    "unknown-vendor-risk-source-"
                                    f"{risk.risk_id}-"
                                    f"{evidence.source_finding_id}"
                                ),
                                description=(
                                    "Risk evidence references an "
                                    "unknown Vendor Research "
                                    "finding."
                                ),
                                severity=(
                                    EvaluationSeverity.CRITICAL
                                ),
                                location=evidence_location,
                                related_ids=[
                                    risk.risk_id,
                                    evidence.source_finding_id,
                                ],
                            )
                        )

                    if evidence.vendor_evidence is None:
                        findings.append(
                            EvaluationFinding(
                                finding_id=(
                                    "missing-vendor-risk-evidence-"
                                    f"{risk.risk_id}-"
                                    f"{evidence_index}"
                                ),
                                description=(
                                    "Vendor Research source does "
                                    "not contain vendor evidence."
                                ),
                                severity=(
                                    EvaluationSeverity.CRITICAL
                                ),
                                location=evidence_location,
                            )
                        )

            if risk.deterministic_score is not None:
                if not risk.deterministic_score.contributing_rule_ids:
                    findings.append(
                        EvaluationFinding(
                            finding_id=(
                                "risk-score-without-rules-"
                                f"{risk.risk_id}"
                            ),
                            description=(
                                "A deterministic risk score does "
                                "not identify contributing rule IDs."
                            ),
                            severity=EvaluationSeverity.HIGH,
                            location=(
                                f"{location}"
                                ".deterministic_score"
                            ),
                            related_ids=[risk.risk_id],
                        )
                    )

    @staticmethod
    def _evaluate_report_references(
        target: RiskReportExecution,
        findings: list[EvaluationFinding],
    ) -> None:
        """Validate reviewer report references."""

        risk_ids = {
            risk.risk_id
            for risk in target.result.risks
        }

        source_finding_ids = {
            *target.source_proposal_finding_ids,
            *target.source_vendor_finding_ids,
        }

        seen_section_ids: set[str] = set()

        for section_index, section in enumerate(
            target.result.reviewer_report.sections
        ):
            location = (
                "result.reviewer_report.sections"
                f"[{section_index}]"
            )

            if section.section_id in seen_section_ids:
                findings.append(
                    EvaluationFinding(
                        finding_id=(
                            "duplicate-report-section-"
                            f"{section.section_id}"
                        ),
                        description=(
                            "The reviewer report contains a "
                            "duplicate section ID."
                        ),
                        severity=EvaluationSeverity.MEDIUM,
                        location=location,
                        related_ids=[section.section_id],
                    )
                )

            seen_section_ids.add(section.section_id)

            unknown_risk_ids = (
                set(section.related_risk_ids)
                - risk_ids
            )

            if unknown_risk_ids:
                findings.append(
                    EvaluationFinding(
                        finding_id=(
                            "unknown-report-risk-reference-"
                            f"{section.section_id}"
                        ),
                        description=(
                            "The reviewer report references risk "
                            "IDs absent from the synthesized risks."
                        ),
                        severity=EvaluationSeverity.HIGH,
                        location=location,
                        related_ids=sorted(
                            unknown_risk_ids
                        ),
                    )
                )

            unknown_finding_ids = (
                set(section.related_finding_ids)
                - source_finding_ids
            )

            if unknown_finding_ids:
                findings.append(
                    EvaluationFinding(
                        finding_id=(
                            "unknown-report-finding-reference-"
                            f"{section.section_id}"
                        ),
                        description=(
                            "The reviewer report references finding "
                            "IDs absent from specialist outputs."
                        ),
                        severity=EvaluationSeverity.HIGH,
                        location=location,
                        related_ids=sorted(
                            unknown_finding_ids
                        ),
                    )
                )

    @staticmethod
    def _calculate_score(
        critical_count: int,
        high_count: int,
        warning_count: int,
    ) -> float:
        """Calculate a bounded deterministic evaluation score."""

        penalty = (
            critical_count * 0.5
            + high_count * 0.25
            + warning_count * 0.1
        )

        return max(
            1.0 - penalty,
            0.0,
        )