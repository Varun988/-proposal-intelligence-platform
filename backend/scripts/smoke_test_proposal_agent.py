import asyncio
import json

from app.agents.proposal_analysis.agent import (
    ProposalAnalysisAgent,
)
from app.agents.proposal_analysis.schemas import (
    ProposalAnalysisInput,
)
from app.core.config import get_settings
from app.core.logging import (
    configure_logging,
    get_logger,
)
from app.evaluation.proposal_analysis import (
    create_proposal_analysis_evaluation_runner,
)
from app.llm.providers.gemini import GeminiProvider
from app.rag.deduplication.content import (
    ContentDeduplicator,
)
from app.rag.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingProvider,
)
from app.rag.reranking.lexical import (
    LexicalRetrievalReranker,
)
from app.rag.vector_store.faiss_store import (
    FaissVectorStore,
)
from app.schemas.chunk import (
    ChunkCitation,
    DocumentChunk,
)
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.tools.registry import ToolRegistry
from app.tools.retrieval_tools import SearchEvidenceTool

ASSESSMENT_ID = "synthetic-assessment-001"
DOCUMENT_ID = "synthetic-proposal-001"
FILE_NAME = "synthetic-vendor-proposal.pdf"


def create_chunk(
    chunk_id: str,
    text: str,
    page_number: int,
    document_chunk_index: int,
) -> DocumentChunk:
    """Create one synthetic proposal evidence chunk."""

    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=DOCUMENT_ID,
        text=text,
        page_number=page_number,
        page_chunk_index=0,
        document_chunk_index=document_chunk_index,
        citation=ChunkCitation(
            document_id=DOCUMENT_ID,
            file_name=FILE_NAME,
            page_number=page_number,
            checksum_sha256="a" * 64,
        ),
        metadata={
            "document_type": "proposal",
            "data_classification": "synthetic",
        },
    )


def create_synthetic_chunks() -> list:
    """Create synthetic evidence for the live agent test."""

    return [
        create_chunk(
            chunk_id="vendor-profile",
            text=(
                "The proposal is submitted by Example Digital "
                "Services for the Enterprise Platform Modernization "
                "Program."
            ),
            page_number=1,
            document_chunk_index=0,
        ),
        create_chunk(
            chunk_id="scope",
            text=(
                "The proposed scope includes solution design, "
                "application development, testing, deployment, "
                "knowledge transfer, and production support."
            ),
            page_number=3,
            document_chunk_index=1,
        ),
        create_chunk(
            chunk_id="delivery",
            text=(
                "The proposed implementation and delivery timeline "
                "is twelve months from contract signature. The plan "
                "contains design, build, test, and deployment phases."
            ),
            page_number=4,
            document_chunk_index=2,
        ),
        create_chunk(
            chunk_id="delivery-duplicate",
            text=(
                "The proposed implementation and delivery timeline "
                "is twelve months from contract signature. The plan "
                "contains design, build, test, and deployment phases."
            ),
            page_number=5,
            document_chunk_index=3,
        ),
        create_chunk(
            chunk_id="staffing",
            text=(
                "The proposed delivery team includes twenty "
                "consultants: two architects, twelve developers, "
                "four test engineers, and two project managers."
            ),
            page_number=7,
            document_chunk_index=4,
        ),
        create_chunk(
            chunk_id="support",
            text=(
                "The vendor will provide application support and "
                "maintenance for three years after production "
                "go-live, with severity-based incident response."
            ),
            page_number=9,
            document_chunk_index=5,
        ),
        create_chunk(
            chunk_id="security",
            text=(
                "Customer information will be encrypted at rest "
                "and in transit. Access will use role-based controls "
                "and multifactor authentication."
            ),
            page_number=12,
            document_chunk_index=6,
        ),
        create_chunk(
            chunk_id="pricing",
            text=(
                "The total proposed fixed implementation price is "
                "two million Australian dollars, excluding applicable "
                "taxes and approved travel expenses."
            ),
            page_number=16,
            document_chunk_index=7,
        ),
        create_chunk(
            chunk_id="assumptions",
            text=(
                "The proposal assumes that the client will provide "
                "timely access to subject-matter experts, existing "
                "system documentation, and required test data."
            ),
            page_number=18,
            document_chunk_index=8,
        ),
        create_chunk(
            chunk_id="exclusions",
            text=(
                "Data cleansing, third-party software licence costs, "
                "and changes to systems outside the agreed scope are "
                "excluded from the fixed implementation price."
            ),
            page_number=19,
            document_chunk_index=9,
        ),
    ]


def build_retrieval_service(
    settings: object,
) -> RetrievalService:
    """Create and populate the real local retrieval pipeline."""

    embedding_provider = SentenceTransformerEmbeddingProvider(
        model_name=settings.embedding_model,
        normalize_embeddings=(settings.normalize_embeddings),
    )

    embedding_service = EmbeddingService(
        provider=embedding_provider,
    )

    embedding_batch = embedding_service.embed_chunks(
        create_synthetic_chunks(),
    )

    vector_store = FaissVectorStore(
        dimension=embedding_batch.dimension,
    )

    vector_store.add(
        embedding_batch.items,
    )

    return RetrievalService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        deduplicator=ContentDeduplicator(
            similarity_threshold=0.9,
        ),
        reranker=LexicalRetrievalReranker(
            retrieval_weight=0.7,
            lexical_weight=0.3,
        ),
        candidate_limit=8,
        final_limit=4,
    )


async def run_smoke_test() -> None:
    """Run and evaluate one live synthetic proposal analysis."""

    settings = get_settings()

    configure_logging(
        log_level=settings.log_level,
        json_format=settings.log_json_format,
    )

    logger = get_logger(__name__)

    logger.info(
        "Live Proposal Analysis Agent smoke test started",
        extra={
            "assessment_id": ASSESSMENT_ID,
            "agent_name": "proposal-analysis",
            "data_classification": "synthetic",
        },
    )

    retrieval_service = build_retrieval_service(
        settings,
    )

    tool_registry = ToolRegistry()
    tool_registry.register(
        SearchEvidenceTool(
            retrieval_service=retrieval_service,
        )
    )

    gemini_provider = GeminiProvider(
        api_key=settings.gemini_api_key,
        model_name=settings.llm_model,
    )

    llm_service = LLMService(
        provider=gemini_provider,
        max_calls_per_assessment=1,
    )

    agent = ProposalAnalysisAgent(
        tool_registry=tool_registry,
        llm_service=llm_service,
        max_tool_calls=5,
    )

    analysis_input = ProposalAnalysisInput(
        assessment_id=ASSESSMENT_ID,
        proposal_document_id=DOCUMENT_ID,
        analysis_objectives=[
            "delivery timeline",
            "pricing and exclusions",
            "security controls",
        ],
        requirements=[
            ("The proposal must provide an implementation timeline and delivery approach.")
        ],
    )

    execution = await agent.analyze(
        analysis_input,
    )

    evaluation_runner = create_proposal_analysis_evaluation_runner()

    evaluation_report = evaluation_runner.run(
        target=execution,
        assessment_id=ASSESSMENT_ID,
        agent_instruction_version=(execution.instruction_version),
    )

    print()
    print("=" * 72)
    print("LIVE SYNTHETIC PROPOSAL ANALYSIS")
    print("=" * 72)
    print(
        json.dumps(
            execution.result.model_dump(
                mode="json",
            ),
            indent=2,
        )
    )

    print()
    print("=" * 72)
    print("AGENT EXECUTION")
    print("=" * 72)
    print(f"Agent: {agent.name}")
    print(f"LLM provider: {execution.llm_provider}")
    print(f"LLM model: {execution.llm_model}")
    print(f"Instruction version: {execution.instruction_version}")
    print(f"Tool calls: {execution.tool_call_count}")
    print(f"Retrieved evidence records: {len(execution.retrieved_evidence)}")
    print(f"Execution time: {execution.total_execution_time_ms:.2f} ms")

    for index, trace in enumerate(
        execution.tool_calls,
        start=1,
    ):
        print(
            f"Tool call {index}: "
            f"{trace.tool_name} | "
            f"results={trace.result_count} | "
            f"success={trace.succeeded}"
        )

    print()
    print("=" * 72)
    print("EVALUATION REPORT")
    print("=" * 72)
    print(f"Evaluation ID: {evaluation_report.evaluation_id}")
    print(f"Overall score: {evaluation_report.overall_score:.2f}")
    print(f"Release approved: {evaluation_report.release_approved}")
    print(f"Blocking gate failures: {evaluation_report.blocking_gate_failure_count}")

    for result in evaluation_report.results:
        print()
        print(f"Evaluator: {result.evaluator_name}")
        print(f"Status: {result.status.value}")
        print(f"Score: {result.score:.2f}")
        print(f"Summary: {result.summary}")

        for finding in result.findings:
            print(f"- [{finding.severity.value}] {finding.description}")

    logger.info(
        "Live Proposal Analysis Agent smoke test completed",
        extra={
            "assessment_id": ASSESSMENT_ID,
            "agent_name": agent.name,
            "tool_call_count": execution.tool_call_count,
            "finding_count": len(execution.result.findings),
            "release_approved": (evaluation_report.release_approved),
            "overall_evaluation_score": (evaluation_report.overall_score),
        },
    )

    if not execution.result.human_review_required:
        raise RuntimeError("Smoke test failed: human review was disabled.")

    if execution.tool_call_count == 0:
        raise RuntimeError("Smoke test failed: no evidence-search tools were executed.")

    if not evaluation_report.release_approved:
        raise RuntimeError(
            "Smoke test completed, but the deterministic evaluation release gates did not pass."
        )

    print()
    print("Validation passed:")
    print("- Proposal Analysis Agent executed")
    print("- Evidence-search tools were called")
    print("- Gemini returned structured output")
    print("- Citations passed deterministic validation")
    print("- Trajectory passed deterministic validation")
    print("- Human review remains required")


if __name__ == "__main__":
    asyncio.run(run_smoke_test())
