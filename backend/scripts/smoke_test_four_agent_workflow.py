import asyncio
import json

from app.agents.orchestrator.agent import OrchestratorAgent
from app.agents.orchestrator.schemas import OrchestratorInput
from app.agents.proposal_analysis.agent import ProposalAnalysisAgent
from app.agents.proposal_analysis.schemas import (
    FindingConfidence,
    ProposalAnalysisInput,
    ProposalAnalysisResult,
    ProposalSummary,
)
from app.agents.risk_report.agent import RiskReportAgent
from app.agents.risk_report.schemas import RiskReportInput
from app.agents.vendor_research.agent import VendorResearchAgent
from app.agents.vendor_research.schemas import VendorResearchInput
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.evaluation.proposal_analysis import (
    create_proposal_analysis_evaluation_runner,
)
from app.evaluation.risk_report import create_risk_report_evaluation_runner
from app.evaluation.vendor_research import (
    create_vendor_research_evaluation_runner,
)
from app.llm.providers.gemini import GeminiProvider
from app.rag.deduplication.content import ContentDeduplicator
from app.rag.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingProvider,
)
from app.rag.reranking.lexical import LexicalRetrievalReranker
from app.rag.vector_store.faiss_store import FaissVectorStore
from app.schemas.chunk import ChunkCitation, DocumentChunk
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.tools.registry import ToolRegistry
from app.tools.retrieval_tools import SearchEvidenceTool
from app.workflows.assessment_graph import create_assessment_graph
from app.workflows.state import AssessmentWorkflowState, WorkflowStatus

ASSESSMENT_ID = "synthetic-four-agent-assessment-001"
PROPOSAL_DOCUMENT_ID = "synthetic-proposal-001"
VENDOR_DOCUMENT_ID = "synthetic-vendor-profile-001"
VENDOR_NAME = "Example Digital Services"
PROPOSAL_FILE_NAME = "synthetic-vendor-proposal.pdf"
VENDOR_FILE_NAME = "synthetic-vendor-profile.pdf"


def create_chunk(
    chunk_id: str,
    document_id: str,
    file_name: str,
    text: str,
    page_number: int,
    document_chunk_index: int,
    metadata: dict[str, object] | None = None,
) -> DocumentChunk:
    """Create one synthetic, citation-ready evidence chunk."""

    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        text=text,
        page_number=page_number,
        page_chunk_index=0,
        document_chunk_index=document_chunk_index,
        citation=ChunkCitation(
            document_id=document_id,
            file_name=file_name,
            page_number=page_number,
            checksum_sha256="a" * 64,
        ),
        metadata={
            "data_classification": "synthetic",
            **(metadata or {}),
        },
    )


def create_synthetic_chunks() -> list[DocumentChunk]:
    """Create proposal and approved synthetic vendor evidence."""

    proposal_chunks = [
        create_chunk(
            "proposal-profile",
            PROPOSAL_DOCUMENT_ID,
            PROPOSAL_FILE_NAME,
            (
                "Example Digital Services submitted this proposal for the "
                "Enterprise Platform Modernization Program."
            ),
            1,
            0,
            {"document_type": "proposal"},
        ),
        create_chunk(
            "proposal-scope",
            PROPOSAL_DOCUMENT_ID,
            PROPOSAL_FILE_NAME,
            (
                "The scope includes solution design, application development, "
                "testing, deployment, knowledge transfer, and production support."
            ),
            3,
            1,
            {"document_type": "proposal"},
        ),
        create_chunk(
            "proposal-delivery",
            PROPOSAL_DOCUMENT_ID,
            PROPOSAL_FILE_NAME,
            (
                "The implementation timeline is twelve months from contract "
                "signature and includes design, build, test, and deployment phases."
            ),
            4,
            2,
            {"document_type": "proposal"},
        ),
        create_chunk(
            "proposal-staffing",
            PROPOSAL_DOCUMENT_ID,
            PROPOSAL_FILE_NAME,
            (
                "The delivery team includes twenty consultants: two architects, "
                "twelve developers, four test engineers, and two project managers."
            ),
            7,
            3,
            {"document_type": "proposal"},
        ),
        create_chunk(
            "proposal-security",
            PROPOSAL_DOCUMENT_ID,
            PROPOSAL_FILE_NAME,
            (
                "Customer information will be encrypted at rest and in transit. "
                "Access uses role-based controls and multifactor authentication."
            ),
            12,
            4,
            {"document_type": "proposal"},
        ),
        create_chunk(
            "proposal-pricing",
            PROPOSAL_DOCUMENT_ID,
            PROPOSAL_FILE_NAME,
            (
                "The fixed implementation price is two million Australian dollars, "
                "excluding taxes, approved travel, and third-party licence costs."
            ),
            16,
            5,
            {"document_type": "proposal"},
        ),
        create_chunk(
            "proposal-assumptions",
            PROPOSAL_DOCUMENT_ID,
            PROPOSAL_FILE_NAME,
            (
                "The client must provide timely access to subject-matter experts, "
                "system documentation, and required test data."
            ),
            18,
            6,
            {"document_type": "proposal"},
        ),
    ]

    vendor_metadata = {
        "document_type": "vendor_profile",
        "source_type": "synthetic_profile",
        "source_name": "Synthetic Vendor Profile",
        "publication_date": "2026-01-01",
        "retrieved_date": "2026-07-17",
    }

    vendor_chunks = [
        create_chunk(
            "vendor-company-profile",
            VENDOR_DOCUMENT_ID,
            VENDOR_FILE_NAME,
            (
                "Example Digital Services was established in 2012 and is "
                "headquartered in Melbourne, Australia."
            ),
            2,
            7,
            {**vendor_metadata, "evidence_category": "company_profile"},
        ),
        create_chunk(
            "vendor-financial",
            VENDOR_DOCUMENT_ID,
            VENDOR_FILE_NAME,
            (
                "The supplied synthetic profile states that the vendor reported "
                "positive operating cash flow for the previous three years. This "
                "is a vendor-profile claim and has not been independently verified."
            ),
            4,
            8,
            {**vendor_metadata, "evidence_category": "financial"},
        ),
        create_chunk(
            "vendor-security",
            VENDOR_DOCUMENT_ID,
            VENDOR_FILE_NAME,
            (
                "The supplied synthetic profile claims current ISO 27001 "
                "certification. Independent certificate validation is unavailable."
            ),
            6,
            9,
            {**vendor_metadata, "evidence_category": "security"},
        ),
        create_chunk(
            "vendor-reputation",
            VENDOR_DOCUMENT_ID,
            VENDOR_FILE_NAME,
            (
                "No adverse events are recorded in the supplied synthetic vendor "
                "profile. No independent reputation source was supplied."
            ),
            8,
            10,
            {**vendor_metadata, "evidence_category": "reputation"},
        ),
    ]

    return [*proposal_chunks, *vendor_chunks]


def build_retrieval_service(settings: object) -> RetrievalService:
    """Build and populate the local retrieval pipeline."""

    provider = SentenceTransformerEmbeddingProvider(
        model_name=settings.embedding_model,
        normalize_embeddings=settings.normalize_embeddings,
    )
    embedding_service = EmbeddingService(provider=provider)
    embedding_batch = embedding_service.embed_chunks(
        create_synthetic_chunks(),
    )
    vector_store = FaissVectorStore(dimension=embedding_batch.dimension)
    vector_store.add(embedding_batch.items)

    return RetrievalService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        deduplicator=ContentDeduplicator(similarity_threshold=0.9),
        reranker=LexicalRetrievalReranker(
            retrieval_weight=0.7,
            lexical_weight=0.3,
        ),
        candidate_limit=10,
        final_limit=5,
    )


def create_placeholder_proposal_result() -> ProposalAnalysisResult:
    """Create identity-valid placeholder data replaced by dynamic handoff."""

    return ProposalAnalysisResult(
        assessment_id=ASSESSMENT_ID,
        proposal_document_id=PROPOSAL_DOCUMENT_ID,
        summary=ProposalSummary(),
        executive_summary=(
            "Placeholder only; replaced by validated workflow output."
        ),
        overall_confidence=FindingConfidence.LOW,
        human_review_required=True,
        analysis_limitations=[
            "Placeholder input; not used as final specialist evidence."
        ],
    )


def print_gate_report(label: str, report: object | None) -> None:
    """Print a compact deterministic evaluation report."""

    print()
    print(label)
    print("-" * len(label))
    if report is None:
        print("No evaluation report available.")
        return

    print(f"Release approved: {report.release_approved}")
    print(f"Overall score: {report.overall_score:.2f}")
    print(
        "Blocking failures: "
        f"{report.blocking_gate_failure_count}"
    )
    for result in report.results:
        print(
            f"- {result.evaluator_name}: "
            f"{result.status.value} ({result.score:.2f})"
        )
        for finding in result.findings:
            print(
                f"  [{finding.severity.value}] "
                f"{finding.description}"
            )


async def run_smoke_test() -> None:
    """Run the complete live synthetic four-agent workflow."""

    settings = get_settings()
    configure_logging(
        log_level=settings.log_level,
        json_format=settings.log_json_format,
    )
    logger = get_logger(__name__)

    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    logger.info(
        "Live synthetic four-agent workflow started",
        extra={
            "assessment_id": ASSESSMENT_ID,
            "data_classification": "synthetic",
            "llm_model": settings.llm_model,
        },
    )

    retrieval_service = build_retrieval_service(settings)
    tool_registry = ToolRegistry()
    tool_registry.register(
        SearchEvidenceTool(retrieval_service=retrieval_service)
    )

    gemini_provider = GeminiProvider(
        api_key=settings.gemini_api_key,
        model_name=settings.llm_model,
    )
    llm_service = LLMService(
        provider=gemini_provider,
        max_calls_per_assessment=3,
    )

    proposal_agent = ProposalAnalysisAgent(
        tool_registry=tool_registry,
        llm_service=llm_service,
        max_tool_calls=6,
    )
    vendor_agent = VendorResearchAgent(
        tool_registry=tool_registry,
        llm_service=llm_service,
        max_tool_calls=6,
    )
    risk_agent = RiskReportAgent(llm_service=llm_service)

    graph = create_assessment_graph(
        orchestrator_agent=OrchestratorAgent(),
        proposal_analysis_agent=proposal_agent,
        proposal_evaluation_runner=(
            create_proposal_analysis_evaluation_runner()
        ),
        vendor_research_agent=vendor_agent,
        vendor_evaluation_runner=(
            create_vendor_research_evaluation_runner()
        ),
        risk_report_agent=risk_agent,
        risk_report_evaluation_runner=(
            create_risk_report_evaluation_runner()
        ),
    )

    state = AssessmentWorkflowState(
        assessment_id=ASSESSMENT_ID,
        proposal_document_id=PROPOSAL_DOCUMENT_ID,
        orchestrator_input=OrchestratorInput(
            assessment_id=ASSESSMENT_ID,
            proposal_document_id=PROPOSAL_DOCUMENT_ID,
            vendor_research_required=True,
            report_required=True,
            human_review_required=True,
        ),
        proposal_analysis_input=ProposalAnalysisInput(
            assessment_id=ASSESSMENT_ID,
            proposal_document_id=PROPOSAL_DOCUMENT_ID,
            analysis_objectives=[
                "scope and delivery timeline",
                "pricing, assumptions, dependencies, and exclusions",
                "staffing, support, and security controls",
            ],
            requirements=[
                (
                    "The proposal must provide an implementation timeline "
                    "and delivery approach."
                )
            ],
        ),
        vendor_research_input=VendorResearchInput(
            assessment_id=ASSESSMENT_ID,
            vendor_name=VENDOR_NAME,
            proposal_document_id=PROPOSAL_DOCUMENT_ID,
            research_objectives=[
                "company profile and ownership",
                "financial information",
                "security posture and certifications",
                "reputation and relevant adverse events",
            ],
            stale_after_days=365,
        ),
        risk_report_input=RiskReportInput(
            assessment_id=ASSESSMENT_ID,
            proposal_document_id=PROPOSAL_DOCUMENT_ID,
            vendor_name=VENDOR_NAME,
            proposal_analysis=create_placeholder_proposal_result(),
            report_objectives=[
                "summarize validated proposal findings",
                "summarize validated vendor research",
                "identify material cross-agent risks",
                "provide mitigations and clarification questions",
                "prepare reviewer and executive reports",
            ],
            human_review_required=True,
        ),
        maximum_steps=12,
        maximum_retries=2,
    )

    result = await graph.ainvoke(state)
    final_state = AssessmentWorkflowState.model_validate(result)

    print()
    print("=" * 78)
    print("LIVE SYNTHETIC FOUR-AGENT WORKFLOW")
    print("=" * 78)
    print(f"Status: {final_state.status.value}")
    print(f"Current step: {final_state.current_step}")
    print(f"Completed agents: {', '.join(final_state.completed_agents)}")
    print(f"Human review required: {final_state.human_review_required}")
    print(f"Human review reason: {final_state.human_review_reason}")
    print(f"Errors: {len(final_state.errors)}")

    print_gate_report(
        "PROPOSAL ANALYSIS EVALUATION",
        final_state.proposal_analysis_evaluation,
    )
    print_gate_report(
        "VENDOR RESEARCH EVALUATION",
        final_state.vendor_research_evaluation,
    )
    print_gate_report(
        "RISK AND REPORT EVALUATION",
        final_state.risk_report_evaluation,
    )

    if final_state.proposal_analysis_execution is not None:
        print()
        print("PROPOSAL ANALYSIS SUMMARY")
        print("-" * 25)
        print(
            json.dumps(
                final_state.proposal_analysis_execution.result.model_dump(
                    mode="json"
                ),
                indent=2,
            )
        )

    if final_state.vendor_research_execution is not None:
        print()
        print("VENDOR RESEARCH SUMMARY")
        print("-" * 23)
        print(
            json.dumps(
                final_state.vendor_research_execution.result.model_dump(
                    mode="json"
                ),
                indent=2,
            )
        )

    if final_state.risk_report_execution is not None:
        print()
        print("RISK AND REPORT SUMMARY")
        print("-" * 23)
        print(
            json.dumps(
                final_state.risk_report_execution.result.model_dump(
                    mode="json"
                ),
                indent=2,
            )
        )

    expected_agents = {
        "orchestrator",
        "proposal-analysis",
        "vendor-research",
        "risk-report",
    }
    completed_agents = set(final_state.completed_agents)

    if final_state.status is not WorkflowStatus.COMPLETED:
        raise RuntimeError(
            "Smoke test failed: workflow did not reach COMPLETED."
        )
    if not expected_agents.issubset(completed_agents):
        raise RuntimeError(
            "Smoke test failed: not all planned agents completed."
        )
    if not final_state.human_review_required:
        raise RuntimeError(
            "Smoke test failed: human review was disabled."
        )
    if final_state.errors:
        raise RuntimeError(
            "Smoke test failed: workflow recorded errors."
        )

    evaluation_reports = [
        final_state.proposal_analysis_evaluation,
        final_state.vendor_research_evaluation,
        final_state.risk_report_evaluation,
    ]
    if any(
        report is None or not report.release_approved
        for report in evaluation_reports
    ):
        raise RuntimeError(
            "Smoke test failed: one or more release gates did not pass."
        )

    logger.info(
        "Live synthetic four-agent workflow completed",
        extra={
            "assessment_id": ASSESSMENT_ID,
            "status": final_state.status.value,
            "completed_agents": final_state.completed_agents,
            "human_review_required": final_state.human_review_required,
            "event_count": len(final_state.events),
        },
    )

    print()
    print("Validation passed:")
    print("- Orchestrator produced the bounded specialist plan")
    print("- Proposal Analysis completed and passed release gates")
    print("- Vendor Research completed and passed release gates")
    print("- Risk input used validated specialist outputs")
    print("- Risk and Report completed and passed its release gate")
    print("- Workflow reached COMPLETED")
    print("- Final business review remains human-owned")


if __name__ == "__main__":
    asyncio.run(run_smoke_test())
