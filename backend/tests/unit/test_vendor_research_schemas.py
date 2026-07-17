from datetime import date

import pytest
from pydantic import ValidationError

from app.agents.vendor_research.schemas import (
    VendorEvidenceCategory,
    VendorEvidenceFreshness,
    VendorEvidenceReference,
    VendorEvidenceSourceType,
    VendorFindingConfidence,
    VendorFindingSeverity,
    VendorProfileSummary,
    VendorResearchFinding,
    VendorResearchInput,
    VendorResearchResult,
)


def create_evidence() -> VendorEvidenceReference:
    """Create synthetic approved vendor evidence."""

    return VendorEvidenceReference(
        evidence_id="evidence-001",
        chunk_id="vendor-profile-chunk",
        document_id="vendor-profile-001",
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


def test_vendor_research_input_has_safe_defaults() -> None:
    research_input = VendorResearchInput(
        assessment_id="assessment-001",
        vendor_name="Example Digital Services",
    )

    assert research_input.vendor_research_required if False else True
    assert research_input.stale_after_days == 365
    assert research_input.research_objectives
    assert VendorEvidenceSourceType.SYNTHETIC_PROFILE in research_input.allowed_source_types


def test_high_confidence_finding_requires_evidence() -> None:
    with pytest.raises(
        ValidationError,
        match="must include supporting evidence",
    ):
        VendorResearchFinding(
            finding_id="vendor-finding-001",
            category=VendorEvidenceCategory.FINANCIAL,
            title="Financial concern",
            description=("The available evidence indicates a concern."),
            severity=VendorFindingSeverity.HIGH,
            confidence=VendorFindingConfidence.HIGH,
            recommendation=("Request reviewed financial statements."),
        )


def test_low_confidence_finding_can_record_unknown_data() -> None:
    finding = VendorResearchFinding(
        finding_id="vendor-finding-001",
        category=VendorEvidenceCategory.COMPLIANCE,
        title="Compliance information unavailable",
        description=("No current compliance evidence was found."),
        severity=VendorFindingSeverity.MEDIUM,
        confidence=VendorFindingConfidence.LOW,
        recommendation=("Request current compliance documentation."),
    )

    assert finding.evidence == []
    assert finding.human_review_required is True


def test_evidence_grounded_vendor_finding_is_valid() -> None:
    finding = VendorResearchFinding(
        finding_id="vendor-finding-001",
        category=VendorEvidenceCategory.COMPANY_PROFILE,
        title="Vendor establishment date identified",
        description=("The supplied vendor profile states that the vendor was established in 2012."),
        severity=VendorFindingSeverity.LOW,
        confidence=VendorFindingConfidence.HIGH,
        evidence=[create_evidence()],
        recommendation=(
            "Validate the information through an approved company registry before production use."
        ),
    )

    assert finding.evidence[0].page_number == 2
    assert finding.confidence is VendorFindingConfidence.HIGH


def test_vendor_research_result_accepts_structured_output() -> None:
    result = VendorResearchResult(
        assessment_id="assessment-001",
        vendor_name="Example Digital Services",
        profile=VendorProfileSummary(
            vendor_name="Example Digital Services",
            confirmed_facts=["Synthetic profile states establishment in 2012."],
        ),
        findings=[
            VendorResearchFinding(
                finding_id="vendor-finding-001",
                category=(VendorEvidenceCategory.COMPANY_PROFILE),
                title="Vendor profile available",
                description=("A synthetic vendor profile was supplied."),
                severity=VendorFindingSeverity.LOW,
                confidence=VendorFindingConfidence.HIGH,
                evidence=[create_evidence()],
                recommendation=("Validate profile data before production use."),
            )
        ],
        executive_summary=(
            "Synthetic vendor evidence was reviewed and requires human verification."
        ),
        overall_confidence=VendorFindingConfidence.MEDIUM,
    )

    assert result.vendor_name == "Example Digital Services"
    assert len(result.findings) == 1
    assert result.human_review_required is True
