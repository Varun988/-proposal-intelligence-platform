from copy import deepcopy
from datetime import date

import pytest

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
from app.evaluation.evaluators.vendor_trajectory import (
    VendorResearchTrajectoryEvaluator,
)
from app.evaluation.schemas import EvaluationStatus


def create_evidence() -> VendorEvidenceReference:
    """Create approved synthetic vendor evidence."""

    return VendorEvidenceReference(
        evidence_id="evidence-vendor-profile",
        chunk_id="vendor-profile",
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
        freshness=VendorEvidenceFreshness.CURRENT,
        retrieval_score=0.90,
        final_score=0.95,
    )


def create_execution() -> VendorResearchExecution:
    """Create a valid Vendor Research execution."""

    evidence = create_evidence()

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
                    "The supplied synthetic profile states that the vendor was established in 2012."
                ),
                severity=VendorFindingSeverity.LOW,
                confidence=VendorFindingConfidence.HIGH,
                evidence=[
                    evidence.model_copy(deep=True),
                ],
                recommendation=("Validate the information through an approved company registry."),
                human_review_required=True,
            )
        ],
        executive_summary=("Synthetic vendor evidence was reviewed."),
        overall_confidence=VendorFindingConfidence.HIGH,
        human_review_required=True,
    )

    return VendorResearchExecution(
        result=result,
        retrieved_evidence=[
            evidence.model_copy(deep=True),
        ],
        tool_calls=[
            VendorResearchToolCallTrace(
                tool_name="search_evidence",
                query=("Find approved company profile evidence for Example Digital Services."),
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


def test_evaluator_passes_valid_trajectory() -> None:
    evaluator = VendorResearchTrajectoryEvaluator()

    result = evaluator.evaluate(
        create_execution(),
    )

    assert result.status is EvaluationStatus.PASSED
    assert result.score == 1.0
    assert result.finding_count == 0
    assert result.metrics["required_tool_used"] is True
    assert result.metrics["successful_tool_calls"] == 1


def test_evaluator_fails_tool_count_mismatch() -> None:
    execution = create_execution()
    execution.tool_call_count = 2

    evaluator = VendorResearchTrajectoryEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    finding_ids = {finding.finding_id for finding in result.findings}

    assert "vendor-tool-call-count-mismatch" in finding_ids


def test_evaluator_fails_tool_call_limit() -> None:
    execution = create_execution()

    execution.tool_calls.append(
        VendorResearchToolCallTrace(
            tool_name="search_evidence",
            query="Find approved financial evidence.",
            succeeded=True,
            execution_time_ms=1.0,
            result_count=1,
        )
    )
    execution.tool_call_count = 2

    evaluator = VendorResearchTrajectoryEvaluator(
        maximum_tool_calls=1,
    )
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    finding_ids = {finding.finding_id for finding in result.findings}

    assert "vendor-tool-call-limit-exceeded" in finding_ids


def test_evaluator_fails_unauthorized_tool() -> None:
    execution = create_execution()

    execution.tool_calls.append(
        VendorResearchToolCallTrace(
            tool_name="browse_unrestricted_web",
            query="Search the internet.",
            succeeded=True,
            execution_time_ms=1.0,
            result_count=1,
        )
    )
    execution.tool_call_count = 2

    evaluator = VendorResearchTrajectoryEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    assert any(
        finding.finding_id.startswith("vendor-unauthorized-tool") for finding in result.findings
    )


def test_evaluator_fails_missing_required_tool() -> None:
    execution = create_execution()

    execution.tool_calls = [
        VendorResearchToolCallTrace(
            tool_name="get_document_page",
            query=None,
            succeeded=True,
            execution_time_ms=1.0,
            result_count=1,
        )
    ]

    evaluator = VendorResearchTrajectoryEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    finding_ids = {finding.finding_id for finding in result.findings}

    assert "vendor-required-tool-not-used" in finding_ids


def test_evaluator_fails_unsuccessful_tool_call() -> None:
    execution = create_execution()

    execution.tool_calls[0] = VendorResearchToolCallTrace(
        tool_name="search_evidence",
        query="Find approved vendor evidence.",
        succeeded=False,
        execution_time_ms=1.0,
        result_count=0,
        error_message="Synthetic search failure.",
    )

    evaluator = VendorResearchTrajectoryEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED
    assert result.metrics["failed_tool_calls"] == 1


def test_evaluator_fails_missing_search_query() -> None:
    execution = create_execution()
    execution.tool_calls[0].query = None

    evaluator = VendorResearchTrajectoryEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    assert any(
        finding.finding_id.startswith("vendor-missing-search-query") for finding in result.findings
    )


def test_evaluator_warns_for_empty_search_result() -> None:
    execution = create_execution()
    execution.tool_calls[0].result_count = 0

    evaluator = VendorResearchTrajectoryEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.WARNING
    assert result.score < 1.0
    assert result.metrics["result_bearing_tool_calls"] == 0


def test_evaluator_fails_instruction_version_mismatch() -> None:
    execution = create_execution()
    execution.instruction_version = "0.9.0"

    evaluator = VendorResearchTrajectoryEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    finding_ids = {finding.finding_id for finding in result.findings}

    assert "vendor-instruction-version-mismatch" in finding_ids


def test_evaluator_fails_disabled_human_review() -> None:
    execution = create_execution()
    execution.result.human_review_required = False

    evaluator = VendorResearchTrajectoryEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    finding_ids = {finding.finding_id for finding in result.findings}

    assert "vendor-human-review-disabled" in finding_ids


def test_evaluator_fails_finding_without_human_review() -> None:
    execution = create_execution()

    modified_finding = deepcopy(execution.result.findings[0])
    modified_finding.human_review_required = False

    execution.result.findings = [
        modified_finding,
    ]

    evaluator = VendorResearchTrajectoryEvaluator()
    result = evaluator.evaluate(execution)

    assert result.status is EvaluationStatus.FAILED

    assert any(
        finding.finding_id.startswith("vendor-finding-human-review-disabled")
        for finding in result.findings
    )


def test_evaluator_rejects_invalid_maximum_tool_calls() -> None:
    with pytest.raises(
        ValueError,
        match="must be at least 1",
    ):
        VendorResearchTrajectoryEvaluator(
            maximum_tool_calls=0,
        )
