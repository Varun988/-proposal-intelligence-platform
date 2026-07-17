from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class VendorEvidenceCategory(StrEnum):
    """Categories supported by vendor research."""

    COMPANY_PROFILE = "company_profile"
    COMPLIANCE = "compliance"
    FINANCIAL = "financial"
    OWNERSHIP = "ownership"
    REPUTATION = "reputation"
    SECURITY = "security"


class VendorEvidenceSourceType(StrEnum):
    """Types of approved vendor-evidence sources."""

    APPROVED_PUBLIC_DOCUMENT = "approved_public_document"
    INTERNAL_RECORD = "internal_record"
    PROVIDED_DOCUMENT = "provided_document"
    SYNTHETIC_PROFILE = "synthetic_profile"


class VendorEvidenceFreshness(StrEnum):
    """Freshness classification assigned to evidence."""

    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"


class VendorFindingSeverity(StrEnum):
    """Severity assigned to a vendor-research finding."""

    CRITICAL = "critical"
    HIGH = "high"
    LOW = "low"
    MEDIUM = "medium"


class VendorFindingConfidence(StrEnum):
    """Confidence assigned to a vendor-research finding."""

    HIGH = "high"
    LOW = "low"
    MEDIUM = "medium"


class VendorEvidenceReference(BaseModel):
    """Evidence used by the Vendor Research Agent."""

    evidence_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    file_name: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    citation_label: str = Field(min_length=1)
    supporting_text: str = Field(min_length=1)

    category: VendorEvidenceCategory
    source_type: VendorEvidenceSourceType
    source_name: str = Field(min_length=1)

    publication_date: date | None = None
    retrieved_date: date | None = None
    freshness: VendorEvidenceFreshness = VendorEvidenceFreshness.UNKNOWN

    retrieval_score: float | None = None
    final_score: float | None = None

    metadata: dict[
        str,
        str | int | float | bool | None,
    ] = Field(default_factory=dict)


class VendorProfileSummary(BaseModel):
    """Structured summary of available vendor information."""

    vendor_name: str = Field(min_length=1)
    legal_name: str | None = None
    headquarters: str | None = None
    ownership_summary: str | None = None
    financial_summary: str | None = None
    security_summary: str | None = None
    compliance_summary: str | None = None
    reputation_summary: str | None = None

    confirmed_facts: list[str] = Field(default_factory=list)
    vendor_claims: list[str] = Field(default_factory=list)
    unavailable_information: list[str] = Field(
        default_factory=list,
    )


class VendorResearchFinding(BaseModel):
    """One evidence-grounded vendor-research finding."""

    finding_id: str = Field(min_length=1)
    category: VendorEvidenceCategory
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    severity: VendorFindingSeverity
    confidence: VendorFindingConfidence

    evidence: list[VendorEvidenceReference] = Field(
        default_factory=list,
    )

    recommendation: str = Field(min_length=1)
    clarification_question: str | None = None
    human_review_required: bool = True

    @model_validator(mode="after")
    def validate_evidence_requirement(
        self,
    ) -> "VendorResearchFinding":
        """Require evidence for medium/high-confidence findings."""

        if self.confidence is not VendorFindingConfidence.LOW and not self.evidence:
            raise ValueError(
                "Medium- and high-confidence vendor findings must include supporting evidence."
            )

        return self


class VendorEvidenceConflict(BaseModel):
    """Conflicting vendor information found across sources."""

    conflict_id: str = Field(min_length=1)
    category: VendorEvidenceCategory
    description: str = Field(min_length=1)
    first_evidence: VendorEvidenceReference
    second_evidence: VendorEvidenceReference
    clarification_question: str = Field(min_length=1)


class VendorResearchInput(BaseModel):
    """Input supplied to the Vendor Research Agent."""

    assessment_id: str = Field(min_length=1)
    vendor_name: str = Field(min_length=1)

    proposal_document_id: str | None = None

    research_objectives: list[str] = Field(
        default_factory=lambda: [
            "company profile and ownership",
            "financial information",
            "security posture and certifications",
            "compliance information",
            "reputation and relevant adverse events",
        ]
    )

    allowed_source_types: list[VendorEvidenceSourceType] = Field(
        default_factory=lambda: [
            VendorEvidenceSourceType.SYNTHETIC_PROFILE,
            VendorEvidenceSourceType.PROVIDED_DOCUMENT,
            VendorEvidenceSourceType.INTERNAL_RECORD,
            VendorEvidenceSourceType.APPROVED_PUBLIC_DOCUMENT,
        ]
    )

    stale_after_days: int = Field(
        default=365,
        ge=1,
        le=3_650,
    )


class VendorResearchResult(BaseModel):
    """Structured result returned by the Vendor Research Agent."""

    assessment_id: str = Field(min_length=1)
    vendor_name: str = Field(min_length=1)

    profile: VendorProfileSummary

    findings: list[VendorResearchFinding] = Field(
        default_factory=list,
    )
    conflicts: list[VendorEvidenceConflict] = Field(
        default_factory=list,
    )
    stale_evidence_ids: list[str] = Field(
        default_factory=list,
    )
    unavailable_information: list[str] = Field(
        default_factory=list,
    )
    clarification_questions: list[str] = Field(
        default_factory=list,
    )

    executive_summary: str = Field(min_length=1)
    overall_confidence: VendorFindingConfidence
    human_review_required: bool = True
    research_limitations: list[str] = Field(
        default_factory=list,
    )


class VendorResearchToolCallTrace(BaseModel):
    """Trace of one tool call made by the agent."""

    tool_name: str = Field(min_length=1)
    query: str | None = None
    succeeded: bool
    execution_time_ms: float = Field(ge=0)
    result_count: int = Field(default=0, ge=0)
    error_message: str | None = None


class VendorResearchExecution(BaseModel):
    """Complete Vendor Research Agent execution result."""

    result: VendorResearchResult

    retrieved_evidence: list[VendorEvidenceReference] = Field(default_factory=list)

    tool_calls: list[VendorResearchToolCallTrace] = Field(
        default_factory=list,
    )

    tool_call_count: int = Field(ge=0)
    llm_provider: str = Field(min_length=1)
    llm_model: str = Field(min_length=1)
    instruction_version: str = Field(min_length=1)
    total_execution_time_ms: float = Field(ge=0)
