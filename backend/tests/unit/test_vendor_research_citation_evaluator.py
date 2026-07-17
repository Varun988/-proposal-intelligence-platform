from copy import deepcopy
from datetime import date

from app.agents.vendor_research.schemas import (
    VendorEvidenceCategory,
    VendorEvidenceFreshness,
    VendorEvidenceReference,
    VendorEvidenceSourceType,
    VendorFindingConfidence,
    VendorFindingSeverity,
    VendorProfileSummary,
    VendorResearchExecution,
    VendorResearchFinding,
    VendorResearchResult,
    VendorResearchToolCallTrace,
)
from app.evaluation.evaluators.vendor_citation import (
    VendorResearchCitationEvaluator,
)
from app.evaluation.schemas import (
    EvaluationSeverity,
    EvaluationStatus,
)


def create_evidence(
    evidence_id: str = "evidence-vendor-profile",
    chunk_id: str = "vendor-profile",
    freshness: VendorEvidenceFreshness = (VendorEvidenceFreshness.CURRENT),
) -> VendorEvidenceReference:
    """Create synthetic vendor evidence."""

    return VendorEvidenceReference(
        evidence_id=evidence_id,
        chunk_id=chunk_id,
        document_id="vendor-document-001",
        file_name="synthetic-vendor-profile.pdf",
        page_number=2,
        citation_label=("synthetic-vendor-profile.pdf, page 2"),
        supporting_text=("Example Digital Services was established in 2012."),
        category=VendorEvidenceCategory.COMPANY_PROFILE,
        source_type=(VendorEvidenceSourceType.SYNTHETIC_PROFILE),
        source_name="Synthetic Vendor Profile",
        publication_date=date(2026, 1, 1),
        retrieved_date=date(2026, 7, 17),
        freshness=freshness,
        retrieval_score=0.90,
        final_score=0.95,
    )


def create_execution(
    freshness: VendorEvidenceFreshness = (VendorEvidenceFreshness.CURRENT),
) -> VendorResearchExecution:
    """Create a valid Vendor Research Agent execution."""

    inventory_evidence = create_evidence(
        freshness=freshness,
    )
    finding_evidence = inventory_evidence.model_copy(
        deep=True,
    )

    stale_ids = []

    if freshness is VendorEvidenceFreshness.STALE:
        stale_ids = [
            inventory_evidence.evidence_id,
        ]

    result = VendorResearchResult(
        assessment_id="assessment-001",
        vendor_name="Example Digital Services",
        profile=VendorProfileSummary(
            vendor_name="Example Digital Services",
            confirmed_facts=[
                ("The synthetic profile states that the vendor was established in 2012.")
            ],
        ),
        findings=[
            VendorResearchFinding(
                finding_id="vendor-finding-001",
                category=(VendorEvidenceCategory.COMPANY_PROFILE),
                title="Vendor establishment date identified",
                description=(
                    "The synthetic profile states that the vendor was established in 2012."
                ),
                severity=VendorFindingSeverity.LOW,
                confidence=VendorFindingConfidence.HIGH,
                evidence=[finding_evidence],
                recommendation=("Validate the date using an approved registry."),
            )
        ],
        stale_evidence_ids=stale_ids,
        executive_summary=("Synthetic vendor evidence was reviewed."),
        overall_confidence=VendorFindingConfidence.HIGH,
    )

    return VendorResearchExecution(
        result=result,
        retrieved_evidence=[
            inventory_evidence,
        ],
        tool_calls=[
            VendorResearchToolCallTrace(
                tool_name="search_evidence",
                query="Find approved vendor profile evidence.",
                succeeded=True,
                execution_time_ms=1.0,
                result_count=1,
            )
        ],
        tool_call_count=1,
        llm_provider="fake",
        llm_model="fake-model",
        instruction_version="1.0.0",
        total_execution_time_ms=10.0,
    )


def test_evaluator_passes_valid_vendor_citation() -> None:
    evaluator = VendorResearchCitationEvaluator()

    result = evaluator.evaluate(
        create_execution(),
    )

    assert result.status is EvaluationStatus.PASSED
    assert result.score == 1.0
    assert result.finding_count == 0
    assert result.metrics["valid_citation_count"] == 1
    assert result.metrics["invalid_citation_count"] == 0


def test_evaluator_fails_unknown_vendor_evidence() -> None:
    execution = create_execution()

    execution.result.findings[0].evidence[0].evidence_id = "unknown-evidence"

    execution.result.findings[0].evidence[0].chunk_id = "unknown-chunk"

    evaluator = VendorResearchCitationEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED
    assert result.critical_finding_count == 1
    assert result.metrics["invalid_citation_count"] == 1


def test_evaluator_fails_mismatched_source_metadata() -> None:
    execution = create_execution()

    execution.result.findings[0].evidence[0].page_number = 99

    evaluator = VendorResearchCitationEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    mismatches = result.findings[0].metadata["mismatched_fields"]

    assert "page_number" in mismatches


def test_evaluator_warns_for_duplicate_citation() -> None:
    execution = create_execution()

    evidence = execution.result.findings[0].evidence[0]

    execution.result.findings[0].evidence = [
        evidence,
        deepcopy(evidence),
    ]

    evaluator = VendorResearchCitationEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.WARNING
    assert result.finding_count == 1
    assert result.findings[0].severity is EvaluationSeverity.LOW
    assert result.metrics["duplicate_citation_count"] == 1


def test_evaluator_allows_low_confidence_without_evidence() -> None:
    execution = create_execution()

    execution.result.findings = [
        VendorResearchFinding(
            finding_id="vendor-finding-002",
            category=VendorEvidenceCategory.COMPLIANCE,
            title="Compliance evidence unavailable",
            description=("No current compliance evidence was retrieved."),
            severity=VendorFindingSeverity.MEDIUM,
            confidence=VendorFindingConfidence.LOW,
            recommendation=("Request current compliance documentation."),
        )
    ]

    evaluator = VendorResearchCitationEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.PASSED
    assert result.score == 1.0
    assert result.metrics["findings_requiring_evidence"] == 0


def test_evaluator_passes_declared_stale_evidence() -> None:
    execution = create_execution(
        freshness=VendorEvidenceFreshness.STALE,
    )

    evaluator = VendorResearchCitationEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.PASSED
    assert result.score == 1.0


def test_evaluator_fails_undeclared_stale_evidence() -> None:
    execution = create_execution(
        freshness=VendorEvidenceFreshness.STALE,
    )

    execution.result.stale_evidence_ids = []

    evaluator = VendorResearchCitationEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    finding_ids = {finding.finding_id for finding in result.findings}

    assert "undeclared-stale-evidence-evidence-vendor-profile" in finding_ids


def test_evaluator_fails_unknown_stale_evidence_id() -> None:
    execution = create_execution()

    execution.result.stale_evidence_ids = [
        "unknown-evidence",
    ]

    evaluator = VendorResearchCitationEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    finding_ids = {finding.finding_id for finding in result.findings}

    assert "unknown-stale-evidence-unknown-evidence" in finding_ids
