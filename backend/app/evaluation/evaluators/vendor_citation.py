from app.agents.vendor_research.policies import (
    VENDOR_RESEARCH_ALLOWED_SOURCE_TYPES,
)
from app.agents.vendor_research.schemas import (
    VendorEvidenceReference,
    VendorEvidenceFreshness,
    VendorFindingConfidence,
    VendorResearchExecution,
    VendorResearchFinding,
)
from app.evaluation.evaluators.base import BaseEvaluator
from app.evaluation.schemas import (
    EvaluationFinding,
    EvaluationResult,
    EvaluationSeverity,
    EvaluationStatus,
)


class VendorResearchCitationEvaluator(
    BaseEvaluator[VendorResearchExecution],
):
    """Evaluate citation coverage and integrity for vendor research."""

    @property
    def name(self) -> str:
        """Return the evaluator name."""

        return "vendor-research-citation-evaluator"

    @property
    def version(self) -> str:
        """Return the evaluator version."""

        return "1.0.0"

    def evaluate(
        self,
        target: VendorResearchExecution,
    ) -> EvaluationResult:
        """Validate findings against retrieved vendor evidence."""

        evaluation_findings: list[EvaluationFinding] = []

        inventory_by_evidence_id = {
            evidence.evidence_id: evidence
            for evidence in target.retrieved_evidence
        }
        inventory_by_chunk_id = {
            evidence.chunk_id: evidence
            for evidence in target.retrieved_evidence
        }

        findings_requiring_evidence = 0
        findings_with_evidence = 0
        valid_citation_count = 0
        invalid_citation_count = 0
        duplicate_citation_count = 0

        allowed_source_types = set(
            VENDOR_RESEARCH_ALLOWED_SOURCE_TYPES
        )

        for finding_index, vendor_finding in enumerate(
            target.result.findings
        ):
            finding_location = (
                f"result.findings[{finding_index}]"
            )

            requires_evidence = (
                vendor_finding.confidence
                is not VendorFindingConfidence.LOW
            )

            if requires_evidence:
                findings_requiring_evidence += 1

            if vendor_finding.evidence:
                findings_with_evidence += 1

            if requires_evidence and not vendor_finding.evidence:
                evaluation_findings.append(
                    EvaluationFinding(
                        finding_id=(
                            "missing-vendor-evidence-"
                            f"{vendor_finding.finding_id}"
                        ),
                        description=(
                            "A medium- or high-confidence vendor "
                            "finding has no supporting evidence."
                        ),
                        severity=EvaluationSeverity.CRITICAL,
                        location=finding_location,
                        related_ids=[
                            vendor_finding.finding_id,
                        ],
                        metadata={
                            "confidence": (
                                vendor_finding.confidence.value
                            ),
                            "category": (
                                vendor_finding.category.value
                            ),
                        },
                    )
                )
                continue

            seen_evidence_ids: set[str] = set()
            seen_chunk_ids: set[str] = set()

            for evidence_index, cited_evidence in enumerate(
                vendor_finding.evidence
            ):
                evidence_location = (
                    f"{finding_location}"
                    f".evidence[{evidence_index}]"
                )

                is_duplicate = (
                    cited_evidence.evidence_id
                    in seen_evidence_ids
                    or cited_evidence.chunk_id
                    in seen_chunk_ids
                )

                if is_duplicate:
                    duplicate_citation_count += 1

                    evaluation_findings.append(
                        EvaluationFinding(
                            finding_id=(
                                "duplicate-vendor-citation-"
                                f"{vendor_finding.finding_id}-"
                                f"{cited_evidence.evidence_id}"
                            ),
                            description=(
                                "The vendor finding contains the "
                                "same evidence citation more than "
                                "once."
                            ),
                            severity=EvaluationSeverity.LOW,
                            location=evidence_location,
                            related_ids=[
                                vendor_finding.finding_id,
                                cited_evidence.evidence_id,
                                cited_evidence.chunk_id,
                            ],
                        )
                    )
                    continue

                seen_evidence_ids.add(
                    cited_evidence.evidence_id
                )
                seen_chunk_ids.add(
                    cited_evidence.chunk_id
                )

                retrieved_evidence = (
                    inventory_by_evidence_id.get(
                        cited_evidence.evidence_id
                    )
                )

                if retrieved_evidence is None:
                    retrieved_evidence = (
                        inventory_by_chunk_id.get(
                            cited_evidence.chunk_id
                        )
                    )

                if retrieved_evidence is None:
                    invalid_citation_count += 1

                    evaluation_findings.append(
                        EvaluationFinding(
                            finding_id=(
                                "unknown-vendor-citation-"
                                f"{vendor_finding.finding_id}-"
                                f"{cited_evidence.evidence_id}"
                            ),
                            description=(
                                "The cited vendor evidence was not "
                                "present in the retrieved evidence "
                                "inventory."
                            ),
                            severity=EvaluationSeverity.CRITICAL,
                            location=evidence_location,
                            related_ids=[
                                vendor_finding.finding_id,
                                cited_evidence.evidence_id,
                                cited_evidence.chunk_id,
                            ],
                        )
                    )
                    continue

                mismatches = self._find_mismatches(
                    actual=cited_evidence,
                    retrieved=retrieved_evidence,
                )

                if mismatches:
                    invalid_citation_count += 1

                    evaluation_findings.append(
                        EvaluationFinding(
                            finding_id=(
                                "vendor-citation-mismatch-"
                                f"{vendor_finding.finding_id}-"
                                f"{cited_evidence.evidence_id}"
                            ),
                            description=(
                                "The vendor citation metadata does "
                                "not match the retrieved evidence."
                            ),
                            severity=EvaluationSeverity.CRITICAL,
                            location=evidence_location,
                            related_ids=[
                                vendor_finding.finding_id,
                                cited_evidence.evidence_id,
                            ],
                            metadata={
                                "mismatched_fields": mismatches,
                            },
                        )
                    )
                    continue

                if (
                    cited_evidence.source_type.value
                    not in allowed_source_types
                ):
                    invalid_citation_count += 1

                    evaluation_findings.append(
                        EvaluationFinding(
                            finding_id=(
                                "unapproved-source-type-"
                                f"{cited_evidence.evidence_id}"
                            ),
                            description=(
                                "The cited vendor evidence uses an "
                                "unapproved source type."
                            ),
                            severity=EvaluationSeverity.CRITICAL,
                            location=evidence_location,
                            related_ids=[
                                cited_evidence.evidence_id,
                            ],
                            metadata={
                                "source_type": (
                                    cited_evidence
                                    .source_type.value
                                ),
                            },
                        )
                    )
                    continue

                if not cited_evidence.supporting_text.strip():
                    invalid_citation_count += 1

                    evaluation_findings.append(
                        EvaluationFinding(
                            finding_id=(
                                "empty-vendor-supporting-text-"
                                f"{cited_evidence.evidence_id}"
                            ),
                            description=(
                                "The vendor citation contains no "
                                "supporting text."
                            ),
                            severity=EvaluationSeverity.HIGH,
                            location=evidence_location,
                            related_ids=[
                                cited_evidence.evidence_id,
                            ],
                        )
                    )
                    continue

                valid_citation_count += 1

        self._evaluate_stale_evidence_declarations(
            target=target,
            findings=evaluation_findings,
        )

        coverage_score = self._calculate_coverage_score(
            findings_requiring_evidence=(
                findings_requiring_evidence
            ),
            findings=target.result.findings,
        )

        integrity_score = self._calculate_integrity_score(
            valid_citation_count=valid_citation_count,
            invalid_citation_count=invalid_citation_count,
        )

        score = (
            coverage_score * 0.5
            + integrity_score * 0.5
        )

        has_blocking_failure = any(
            finding.severity
            in {
                EvaluationSeverity.CRITICAL,
                EvaluationSeverity.HIGH,
            }
            for finding in evaluation_findings
        )

        warning_only = (
            bool(evaluation_findings)
            and not has_blocking_failure
        )

        if has_blocking_failure:
            status = EvaluationStatus.FAILED
            summary = (
                "One or more vendor findings contain missing "
                "or invalid evidence citations."
            )
        elif warning_only:
            status = EvaluationStatus.WARNING
            summary = (
                "Vendor citation validation completed with "
                "non-blocking warnings."
            )
        else:
            status = EvaluationStatus.PASSED
            summary = (
                "Vendor findings passed citation coverage and "
                "integrity validation."
            )

        return EvaluationResult(
            evaluator_name=self.name,
            evaluator_version=self.version,
            status=status,
            score=score,
            summary=summary,
            findings=evaluation_findings,
            metrics={
                "total_findings": len(
                    target.result.findings
                ),
                "findings_requiring_evidence": (
                    findings_requiring_evidence
                ),
                "findings_with_evidence": (
                    findings_with_evidence
                ),
                "valid_citation_count": valid_citation_count,
                "invalid_citation_count": (
                    invalid_citation_count
                ),
                "duplicate_citation_count": (
                    duplicate_citation_count
                ),
                "retrieved_evidence_count": len(
                    target.retrieved_evidence
                ),
                "citation_coverage": coverage_score,
                "citation_integrity": integrity_score,
            },
        )

    @staticmethod
    def _find_mismatches(
        actual: VendorEvidenceReference,
        retrieved: VendorEvidenceReference,
    ) -> list:
        """Return fields that differ from retrieved evidence."""

        compared_fields = (
            "evidence_id",
            "chunk_id",
            "document_id",
            "file_name",
            "page_number",
            "citation_label",
            "category",
            "source_type",
            "source_name",
            "publication_date",
            "retrieved_date",
            "freshness",
        )

        return [
            field_name
            for field_name in compared_fields
            if getattr(actual, field_name)
            != getattr(retrieved, field_name)
        ]

    @staticmethod
    def _evaluate_stale_evidence_declarations(
        target: VendorResearchExecution,
        findings: list[EvaluationFinding],
    ) -> None:
        """Ensure stale evidence is declared in the result."""

        declared_stale_ids = set(
            target.result.stale_evidence_ids
        )

        actual_stale_ids = {
            evidence.evidence_id
            for evidence in target.retrieved_evidence
            if evidence.freshness
            is VendorEvidenceFreshness.STALE
        }

        missing_declarations = (
            actual_stale_ids - declared_stale_ids
        )

        unknown_declarations = (
            declared_stale_ids
            - {
                evidence.evidence_id
                for evidence in target.retrieved_evidence
            }
        )

        for evidence_id in sorted(
            missing_declarations
        ):
            findings.append(
                EvaluationFinding(
                    finding_id=(
                        "undeclared-stale-evidence-"
                        f"{evidence_id}"
                    ),
                    description=(
                        "Retrieved stale evidence was not declared "
                        "in stale_evidence_ids."
                    ),
                    severity=EvaluationSeverity.HIGH,
                    location="result.stale_evidence_ids",
                    related_ids=[evidence_id],
                )
            )

        for evidence_id in sorted(
            unknown_declarations
        ):
            findings.append(
                EvaluationFinding(
                    finding_id=(
                        "unknown-stale-evidence-"
                        f"{evidence_id}"
                    ),
                    description=(
                        "stale_evidence_ids contains an evidence "
                        "ID absent from retrieved evidence."
                    ),
                    severity=EvaluationSeverity.HIGH,
                    location="result.stale_evidence_ids",
                    related_ids=[evidence_id],
                )
            )

    @staticmethod
    def _calculate_coverage_score(
        findings_requiring_evidence: int,
        findings: list[VendorResearchFinding],
    ) -> float:
        """Calculate finding-level evidence coverage."""

        if findings_requiring_evidence == 0:
            return 1.0

        covered_findings = sum(
            1
            for finding in findings
            if (
                finding.confidence
                is not VendorFindingConfidence.LOW
                and bool(finding.evidence)
            )
        )

        return (
            covered_findings
            / findings_requiring_evidence
        )

    @staticmethod
    def _calculate_integrity_score(
        valid_citation_count: int,
        invalid_citation_count: int,
    ) -> float:
        """Calculate evidence-citation integrity."""

        citation_count = (
            valid_citation_count
            + invalid_citation_count
        )

        if citation_count == 0:
            return 1.0

        return valid_citation_count / citation_count