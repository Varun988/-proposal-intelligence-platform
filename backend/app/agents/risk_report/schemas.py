from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from app.agents.proposal_analysis.schemas import (
    EvidenceReference,
    ProposalAnalysisResult,
)
from app.agents.vendor_research.schemas import (
    VendorEvidenceReference,
    VendorResearchResult,
)


class RiskCategory(StrEnum):
    """Categories supported by risk and report synthesis."""

    COMMERCIAL = "commercial"
    COMPLIANCE = "compliance"
    DELIVERY = "delivery"
    FINANCIAL = "financial"
    LEGAL = "legal"
    REPUTATION = "reputation"
    SECURITY = "security"
    STRATEGIC = "strategic"


class RiskSeverity(StrEnum):
    """Severity assigned to a synthesized risk."""

    CRITICAL = "critical"
    HIGH = "high"
    LOW = "low"
    MEDIUM = "medium"


class RiskConfidence(StrEnum):
    """Confidence assigned to a synthesized risk."""

    HIGH = "high"
    LOW = "low"
    MEDIUM = "medium"


class RiskStatus(StrEnum):
    """Review status of a synthesized risk."""

    OPEN = "open"
    PENDING_CLARIFICATION = "pending_clarification"
    REQUIRES_SPECIALIST_REVIEW = "requires_specialist_review"


class DeterministicRiskScore(BaseModel):
    """Official risk score produced by deterministic rules."""

    score: int = Field(ge=0, le=100)
    band: str = Field(min_length=1)
    rule_version: str = Field(min_length=1)

    contributing_rule_ids: list[str] = Field(
        default_factory=list,
    )

    explanation: str = Field(min_length=1)


class RiskEvidenceReference(BaseModel):
    """Evidence supporting a synthesized risk."""

    source_agent: str = Field(min_length=1)
    source_finding_id: str = Field(min_length=1)

    proposal_evidence: EvidenceReference | None = None
    vendor_evidence: VendorEvidenceReference | None = None

    @model_validator(mode="after")
    def validate_evidence_source(
        self,
    ) -> "RiskEvidenceReference":
        """Require exactly one concrete evidence reference."""

        evidence_count = sum(
            [
                self.proposal_evidence is not None,
                self.vendor_evidence is not None,
            ]
        )

        if evidence_count != 1:
            raise ValueError(
                "Risk evidence must contain exactly one proposal or vendor evidence reference."
            )

        return self


class SynthesizedRisk(BaseModel):
    """One evidence-grounded cross-agent risk."""

    risk_id: str = Field(min_length=1)
    category: RiskCategory
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)

    severity: RiskSeverity
    confidence: RiskConfidence
    status: RiskStatus = RiskStatus.OPEN

    evidence: list[RiskEvidenceReference] = Field(
        default_factory=list,
    )

    business_impact: str = Field(min_length=1)
    mitigation: str = Field(min_length=1)
    clarification_question: str | None = None

    deterministic_score: DeterministicRiskScore | None = None
    human_review_required: bool = True

    @model_validator(mode="after")
    def validate_evidence_requirement(
        self,
    ) -> "SynthesizedRisk":
        """Require evidence for medium/high-confidence risks."""

        if self.confidence is not RiskConfidence.LOW and not self.evidence:
            raise ValueError("Medium- and high-confidence risks must include supporting evidence.")

        return self


class ReportSection(BaseModel):
    """One structured section of a generated report."""

    section_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)

    related_risk_ids: list[str] = Field(
        default_factory=list,
    )
    related_finding_ids: list[str] = Field(
        default_factory=list,
    )


class ReviewerReport(BaseModel):
    """Detailed report intended for specialist reviewers."""

    title: str = Field(min_length=1)
    purpose: str = Field(min_length=1)

    sections: list[ReportSection] = Field(
        default_factory=list,
    )

    unresolved_questions: list[str] = Field(
        default_factory=list,
    )
    required_human_actions: list[str] = Field(
        default_factory=list,
    )


class ExecutiveReport(BaseModel):
    """Concise decision-support report for management."""

    title: str = Field(min_length=1)
    executive_summary: str = Field(min_length=1)
    key_strengths: list[str] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    unresolved_decisions: list[str] = Field(
        default_factory=list,
    )
    proposed_conditions: list[str] = Field(
        default_factory=list,
    )
    decision_disclaimer: str = Field(min_length=1)


class RiskReportInput(BaseModel):
    """Input supplied to the Risk and Report Agent."""

    assessment_id: str = Field(min_length=1)
    proposal_document_id: str = Field(min_length=1)
    vendor_name: str = Field(min_length=1)

    proposal_analysis: ProposalAnalysisResult
    vendor_research: VendorResearchResult | None = None

    deterministic_scores: list[DeterministicRiskScore] = Field(default_factory=list)

    report_objectives: list[str] = Field(
        default_factory=lambda: [
            "summarize validated proposal findings",
            "summarize validated vendor research",
            "identify material cross-agent risks",
            "provide mitigations and clarification questions",
            "prepare reviewer and executive reports",
        ]
    )

    human_review_required: bool = True

    @model_validator(mode="after")
    def validate_identity_consistency(
        self,
    ) -> "RiskReportInput":
        """Validate identities across specialist-agent outputs."""

        if self.proposal_analysis.assessment_id != self.assessment_id:
            raise ValueError(
                "Proposal analysis assessment ID must match the Risk and Report assessment ID."
            )

        if self.proposal_analysis.proposal_document_id != self.proposal_document_id:
            raise ValueError(
                "Proposal analysis document ID must match the Risk and Report proposal document ID."
            )

        if (
            self.vendor_research is not None
            and self.vendor_research.assessment_id != self.assessment_id
        ):
            raise ValueError(
                "Vendor research assessment ID must match the Risk and Report assessment ID."
            )

        if (
            self.vendor_research is not None
            and self.vendor_research.vendor_name.casefold() != self.vendor_name.casefold()
        ):
            raise ValueError(
                "Vendor research vendor name must match the Risk and Report vendor name."
            )

        return self


class RiskReportResult(BaseModel):
    """Structured result returned by the Risk and Report Agent."""

    assessment_id: str = Field(min_length=1)
    proposal_document_id: str = Field(min_length=1)
    vendor_name: str = Field(min_length=1)

    risks: list[SynthesizedRisk] = Field(
        default_factory=list,
    )

    reviewer_report: ReviewerReport
    executive_report: ExecutiveReport

    clarification_questions: list[str] = Field(
        default_factory=list,
    )
    analysis_limitations: list[str] = Field(
        default_factory=list,
    )

    overall_confidence: RiskConfidence
    human_review_required: bool = True
    official_decision_provided: bool = False

    @model_validator(mode="after")
    def prevent_automated_decision(
        self,
    ) -> "RiskReportResult":
        """Prevent the agent from producing an official decision."""

        if self.official_decision_provided:
            raise ValueError(
                "The Risk and Report Agent cannot provide an official vendor decision."
            )

        if not self.human_review_required:
            raise ValueError("Risk and Report output must require human review.")

        return self


class RiskReportExecution(BaseModel):
    """Complete Risk and Report Agent execution result."""

    result: RiskReportResult

    source_proposal_finding_ids: list[str] = Field(
        default_factory=list,
    )
    source_vendor_finding_ids: list[str] = Field(
        default_factory=list,
    )

    llm_provider: str = Field(min_length=1)
    llm_model: str = Field(min_length=1)
    instruction_version: str = Field(min_length=1)

    total_execution_time_ms: float = Field(ge=0)
