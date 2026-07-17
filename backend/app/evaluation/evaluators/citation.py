from app.agents.proposal_analysis.schemas import (
    EvidenceReference,
    FindingConfidence,
    ProposalAnalysisExecution,
)
from app.evaluation.evaluators.base import BaseEvaluator
from app.evaluation.schemas import (
    EvaluationFinding,
    EvaluationResult,
    EvaluationSeverity,
    EvaluationStatus,
)


class ProposalCitationEvaluator(
    BaseEvaluator[ProposalAnalysisExecution],
):
    """Evaluate citation coverage and integrity for proposal findings."""

    @property
    def name(self) -> str:
        """Return the evaluator name."""

        return "proposal-citation-evaluator"

    @property
    def version(self) -> str:
        """Return the evaluator version."""

        return "1.0.0"

    def evaluate(
        self,
        target: ProposalAnalysisExecution,
    ) -> EvaluationResult:
        """Evaluate citations against the retrieved evidence inventory."""

        evaluation_findings: list[EvaluationFinding] = []

        evidence_inventory = {evidence.chunk_id: evidence for evidence in target.retrieved_evidence}

        total_findings = len(target.result.findings)
        findings_requiring_evidence = 0
        findings_with_evidence = 0
        valid_citation_count = 0
        invalid_citation_count = 0

        for finding_index, proposal_finding in enumerate(target.result.findings):
            location = f"result.findings[{finding_index}]"

            requires_evidence = proposal_finding.confidence is not FindingConfidence.LOW

            if requires_evidence:
                findings_requiring_evidence += 1

            if proposal_finding.evidence:
                findings_with_evidence += 1

            if requires_evidence and not proposal_finding.evidence:
                evaluation_findings.append(
                    EvaluationFinding(
                        finding_id=(f"missing-evidence-{proposal_finding.finding_id}"),
                        description=(
                            "A medium- or high-confidence finding "
                            "does not include supporting evidence."
                        ),
                        severity=EvaluationSeverity.CRITICAL,
                        location=location,
                        related_ids=[
                            proposal_finding.finding_id,
                        ],
                        metadata={
                            "confidence": (proposal_finding.confidence.value),
                            "category": (proposal_finding.category.value),
                        },
                    )
                )

                continue

            seen_chunk_ids: set[str] = set()

            for evidence_index, evidence in enumerate(proposal_finding.evidence):
                evidence_location = f"{location}.evidence[{evidence_index}]"

                if evidence.chunk_id in seen_chunk_ids:
                    evaluation_findings.append(
                        EvaluationFinding(
                            finding_id=(
                                "duplicate-citation-"
                                f"{proposal_finding.finding_id}-"
                                f"{evidence.chunk_id}"
                            ),
                            description=("The finding contains the same citation more than once."),
                            severity=EvaluationSeverity.LOW,
                            location=evidence_location,
                            related_ids=[
                                proposal_finding.finding_id,
                                evidence.chunk_id,
                            ],
                        )
                    )

                    continue

                seen_chunk_ids.add(evidence.chunk_id)

                retrieved_evidence = evidence_inventory.get(
                    evidence.chunk_id,
                )

                if retrieved_evidence is None:
                    invalid_citation_count += 1

                    evaluation_findings.append(
                        EvaluationFinding(
                            finding_id=(
                                "unknown-citation-"
                                f"{proposal_finding.finding_id}-"
                                f"{evidence.chunk_id}"
                            ),
                            description=(
                                "The cited chunk was not present in the agent's retrieved evidence."
                            ),
                            severity=EvaluationSeverity.CRITICAL,
                            location=evidence_location,
                            related_ids=[
                                proposal_finding.finding_id,
                                evidence.chunk_id,
                            ],
                        )
                    )

                    continue

                mismatches = self._find_mismatches(
                    actual=evidence,
                    retrieved=retrieved_evidence,
                )

                if mismatches:
                    invalid_citation_count += 1

                    evaluation_findings.append(
                        EvaluationFinding(
                            finding_id=(
                                "citation-mismatch-"
                                f"{proposal_finding.finding_id}-"
                                f"{evidence.chunk_id}"
                            ),
                            description=(
                                "The citation metadata does not match "
                                "the retrieved source evidence."
                            ),
                            severity=EvaluationSeverity.CRITICAL,
                            location=evidence_location,
                            related_ids=[
                                proposal_finding.finding_id,
                                evidence.chunk_id,
                            ],
                            metadata={
                                "mismatched_fields": mismatches,
                            },
                        )
                    )

                    continue

                if not evidence.supporting_text.strip():
                    invalid_citation_count += 1

                    evaluation_findings.append(
                        EvaluationFinding(
                            finding_id=(
                                "empty-supporting-text-"
                                f"{proposal_finding.finding_id}-"
                                f"{evidence.chunk_id}"
                            ),
                            description=("The citation has no supporting text."),
                            severity=EvaluationSeverity.HIGH,
                            location=evidence_location,
                            related_ids=[
                                proposal_finding.finding_id,
                                evidence.chunk_id,
                            ],
                        )
                    )

                    continue

                valid_citation_count += 1

        coverage_score = self._calculate_coverage_score(
            findings_requiring_evidence=(findings_requiring_evidence),
            findings=target.result.findings,
        )

        integrity_score = self._calculate_integrity_score(
            valid_citation_count=valid_citation_count,
            invalid_citation_count=invalid_citation_count,
        )

        score = coverage_score * 0.5 + integrity_score * 0.5

        has_blocking_failure = any(
            finding.severity is EvaluationSeverity.CRITICAL for finding in evaluation_findings
        )

        status = EvaluationStatus.FAILED if has_blocking_failure else EvaluationStatus.PASSED

        if status is EvaluationStatus.PASSED:
            summary = "Proposal finding citations passed coverage and integrity validation."
        else:
            summary = "One or more proposal findings have missing or invalid citations."

        return EvaluationResult(
            evaluator_name=self.name,
            evaluator_version=self.version,
            status=status,
            score=score,
            summary=summary,
            findings=evaluation_findings,
            metrics={
                "total_findings": total_findings,
                "findings_requiring_evidence": (findings_requiring_evidence),
                "findings_with_evidence": (findings_with_evidence),
                "valid_citation_count": valid_citation_count,
                "invalid_citation_count": (invalid_citation_count),
                "retrieved_evidence_count": len(target.retrieved_evidence),
                "citation_coverage": coverage_score,
                "citation_integrity": integrity_score,
            },
        )

    @staticmethod
    def _find_mismatches(
        actual: EvidenceReference,
        retrieved: EvidenceReference,
    ) -> list:
        """Return citation fields that differ from retrieved evidence."""

        mismatches: list[str] = []

        if actual.document_id != retrieved.document_id:
            mismatches.append("document_id")

        if actual.file_name != retrieved.file_name:
            mismatches.append("file_name")

        if actual.page_number != retrieved.page_number:
            mismatches.append("page_number")

        if actual.citation_label != retrieved.citation_label:
            mismatches.append("citation_label")

        return mismatches

    @staticmethod
    def _calculate_coverage_score(
        findings_requiring_evidence: int,
        findings: list,
    ) -> float:
        """Calculate finding-level citation coverage."""

        if findings_requiring_evidence == 0:
            return 1.0

        covered_findings = sum(
            1
            for finding in findings
            if (finding.confidence is not FindingConfidence.LOW and bool(finding.evidence))
        )

        return covered_findings / findings_requiring_evidence

    @staticmethod
    def _calculate_integrity_score(
        valid_citation_count: int,
        invalid_citation_count: int,
    ) -> float:
        """Calculate citation integrity across cited evidence."""

        total_citations = valid_citation_count + invalid_citation_count

        if total_citations == 0:
            return 1.0

        return valid_citation_count / total_citations
