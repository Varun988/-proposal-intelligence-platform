from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class FindingCategory(StrEnum):
    """Categories supported by the Proposal Analysis Agent."""

    COMMERCIAL = "commercial"
    COMPLIANCE = "compliance"
    DELIVERY = "delivery"
    GENERAL = "general"
    SECURITY = "security"


class FindingSeverity(StrEnum):
    """Severity assigned to a proposal finding."""

    CRITICAL = "critical"
    HIGH = "high"
    LOW = "low"
    MEDIUM = "medium"


class FindingConfidence(StrEnum):
    """Confidence assigned to an agent-generated finding."""

    HIGH = "high"
    LOW = "low"
    MEDIUM = "medium"


class RequirementStatus(StrEnum):
    """Status of a proposal response against a requirement."""

    COMPLIANT = "compliant"
    EVIDENCE_NOT_FOUND = "evidence_not_found"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    UNCLEAR = "unclear"


class EvidenceReference(BaseModel):
    """Evidence supporting an agent conclusion."""

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    file_name: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    citation_label: str = Field(min_length=1)
    supporting_text: str = Field(min_length=1)
    retrieval_score: float | None = None
    final_score: float | None = None


class ProposalSummary(BaseModel):
    """Structured summary of a vendor proposal."""

    vendor_name: str | None = None
    proposal_title: str | None = None
    scope_summary: str | None = None
    delivery_timeline: str | None = None
    pricing_summary: str | None = None
    support_summary: str | None = None
    staffing_summary: str | None = None
    security_summary: str | None = None

    assumptions: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)


class RequirementAssessment(BaseModel):
    """Assessment of one requirement against proposal evidence."""

    requirement_id: str = Field(min_length=1)
    requirement_text: str = Field(min_length=1)
    status: RequirementStatus
    explanation: str = Field(min_length=1)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    clarification_question: str | None = None


class ProposalFinding(BaseModel):
    """One evidence-grounded proposal finding."""

    finding_id: str = Field(min_length=1)
    category: FindingCategory
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    severity: FindingSeverity
    confidence: FindingConfidence
    evidence: list[EvidenceReference] = Field(default_factory=list)
    recommendation: str = Field(min_length=1)
    human_review_required: bool = True

    @model_validator(mode="after")
    def validate_evidence_requirement(self) -> "ProposalFinding":
        """Require evidence unless confidence is explicitly low."""

        if self.confidence is not FindingConfidence.LOW and not self.evidence:
            raise ValueError(
                "Medium- and high-confidence findings must include supporting evidence."
            )

        return self


class MissingInformationItem(BaseModel):
    """Information required but not found in the proposal evidence."""

    item_id: str = Field(min_length=1)
    category: FindingCategory
    description: str = Field(min_length=1)
    business_impact: str = Field(min_length=1)
    clarification_question: str = Field(min_length=1)


class ContradictionItem(BaseModel):
    """Contradictory statements detected in proposal evidence."""

    contradiction_id: str = Field(min_length=1)
    category: FindingCategory
    description: str = Field(min_length=1)
    first_evidence: EvidenceReference
    second_evidence: EvidenceReference
    clarification_question: str = Field(min_length=1)


class ProposalAnalysisInput(BaseModel):
    """Input supplied to the Proposal Analysis Agent."""

    assessment_id: str = Field(min_length=1)
    proposal_document_id: str = Field(min_length=1)
    rfp_document_id: str | None = None
    analysis_objectives: list[str] = Field(
        default_factory=lambda: [
            "scope",
            "delivery timeline",
            "pricing",
            "staffing",
            "assumptions",
            "dependencies",
            "exclusions",
            "security",
            "support",
        ]
    )
    requirements: list[str] = Field(default_factory=list)


class ProposalAnalysisResult(BaseModel):
    """Structured result returned by the Proposal Analysis Agent."""

    assessment_id: str = Field(min_length=1)
    proposal_document_id: str = Field(min_length=1)
    summary: ProposalSummary

    requirement_assessments: list[RequirementAssessment] = Field(
        default_factory=list,
    )
    findings: list[ProposalFinding] = Field(default_factory=list)
    missing_information: list[MissingInformationItem] = Field(
        default_factory=list,
    )
    contradictions: list[ContradictionItem] = Field(
        default_factory=list,
    )

    executive_summary: str = Field(min_length=1)
    overall_confidence: FindingConfidence
    human_review_required: bool = True
    analysis_limitations: list[str] = Field(default_factory=list)


class AgentToolCallTrace(BaseModel):
    """Trace of one tool call made by the agent."""

    tool_name: str = Field(min_length=1)
    query: str | None = None
    succeeded: bool
    execution_time_ms: float = Field(ge=0)
    result_count: int = Field(default=0, ge=0)
    error_message: str | None = None


class ProposalAnalysisExecution(BaseModel):
    """Complete Proposal Analysis Agent execution result."""

    result: ProposalAnalysisResult

    retrieved_evidence: list[EvidenceReference] = Field(
        default_factory=list,
    )

    tool_calls: list[AgentToolCallTrace] = Field(
        default_factory=list,
    )

    tool_call_count: int = Field(ge=0)
    llm_provider: str = Field(min_length=1)
    llm_model: str = Field(min_length=1)
    instruction_version: str = Field(min_length=1)
    total_execution_time_ms: float = Field(ge=0)
