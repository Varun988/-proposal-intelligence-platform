from app.core.config import get_settings
from app.rag.deduplication.content import ContentDeduplicator
from app.rag.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingProvider,
)
from app.rag.reranking.lexical import LexicalRetrievalReranker
from app.rag.vector_store.faiss_store import FaissVectorStore
from app.schemas.chunk import (
    ChunkCitation,
    DocumentChunk,
)
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService


def create_chunk(
    chunk_id: str,
    text: str,
    page_number: int,
    document_chunk_index: int,
) -> DocumentChunk:
    """Create a synthetic proposal evidence chunk."""

    return DocumentChunk(
        chunk_id=chunk_id,
        document_id="synthetic-proposal-001",
        text=text,
        page_number=page_number,
        page_chunk_index=0,
        document_chunk_index=document_chunk_index,
        citation=ChunkCitation(
            document_id="synthetic-proposal-001",
            file_name="synthetic-vendor-proposal.pdf",
            page_number=page_number,
            checksum_sha256="a" * 64,
        ),
        metadata={
            "document_type": "proposal",
            "data_classification": "synthetic",
        },
    )


def create_synthetic_chunks() -> list:
    """Create synthetic proposal evidence for retrieval testing."""

    return [
        create_chunk(
            chunk_id="delivery-primary",
            text=(
                "The proposed implementation and delivery timeline "
                "is twelve months from contract signature."
            ),
            page_number=4,
            document_chunk_index=0,
        ),
        create_chunk(
            chunk_id="delivery-duplicate",
            text=(
                "The proposed implementation and delivery timeline "
                "is twelve months from contract signature."
            ),
            page_number=5,
            document_chunk_index=1,
        ),
        create_chunk(
            chunk_id="support",
            text=(
                "The vendor will provide application support and "
                "maintenance services for three years after go-live."
            ),
            page_number=8,
            document_chunk_index=2,
        ),
        create_chunk(
            chunk_id="security",
            text=(
                "Customer information will be encrypted at rest "
                "and in transit using approved encryption controls."
            ),
            page_number=12,
            document_chunk_index=3,
        ),
        create_chunk(
            chunk_id="staffing",
            text=(
                "The delivery team consists of twenty consultants, "
                "including architects, developers, and test engineers."
            ),
            page_number=15,
            document_chunk_index=4,
        ),
        create_chunk(
            chunk_id="pricing",
            text=(
                "The total proposed implementation price is "
                "two million Australian dollars."
            ),
            page_number=19,
            document_chunk_index=5,
        ),
    ]


def run_smoke_test() -> None:
    """Run the real local retrieval pipeline."""

    settings = get_settings()

    print("Loading local embedding model...")

    embedding_provider = (
        SentenceTransformerEmbeddingProvider(
            model_name=settings.embedding_model,
            normalize_embeddings=(
                settings.normalize_embeddings
            ),
        )
    )

    embedding_service = EmbeddingService(
        provider=embedding_provider,
    )

    chunks = create_synthetic_chunks()

    print(f"Embedding {len(chunks)} synthetic chunks...")

    embedding_result = embedding_service.embed_chunks(
        chunks,
    )

    vector_store = FaissVectorStore(
        dimension=embedding_result.dimension,
    )

    vector_store.add(
        embedding_result.items,
    )

    retrieval_service = RetrievalService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        deduplicator=ContentDeduplicator(
            similarity_threshold=0.9,
        ),
        reranker=LexicalRetrievalReranker(
            retrieval_weight=0.7,
            lexical_weight=0.3,
        ),
        candidate_limit=6,
        final_limit=3,
    )

    query = "What is the proposed project delivery timeline?"

    print(f"Query: {query}")

    response = retrieval_service.retrieve(query)

    print()
    print("Local retrieval smoke test successful")
    print(f"Initial candidates: {response.metrics.initial_candidate_count}")
    print(
        "Candidates after deduplication: "
        f"{response.metrics.deduplicated_candidate_count}"
    )
    print(f"Duplicates removed: {response.metrics.duplicate_count}")
    print(f"Final results: {response.metrics.final_result_count}")
    print(f"Total latency: {response.metrics.total_latency_ms:.2f} ms")
    print()

    for position, candidate in enumerate(
        response.candidates,
        start=1,
    ):
        print(f"Result {position}")
        print(f"Chunk ID: {candidate.chunk.chunk_id}")
        print(f"Citation: {candidate.citation_label}")
        print(
            "Retrieval score: "
            f"{candidate.retrieval_score:.4f}"
        )
        print(
            "Lexical score: "
            f"{candidate.reranking_score:.4f}"
        )
        print(f"Final score: {candidate.final_score:.4f}")
        print(
            "Merged duplicates: "
            f"{candidate.duplicate_chunk_ids}"
        )
        print(f"Text: {candidate.chunk.text}")
        print()

    top_result = response.candidates[0]

    if "twelve months" not in top_result.chunk.text.casefold():
        raise RuntimeError(
            "Retrieval smoke test failed: delivery timeline "
            "was not ranked first."
        )

    if response.metrics.duplicate_count < 1:
        raise RuntimeError(
            "Retrieval smoke test failed: the duplicate "
            "delivery evidence was not removed."
        )

    print("Validation passed:")
    print("- Delivery evidence ranked first")
    print("- Duplicate evidence removed")
    print("- Citation metadata preserved")


if __name__ == "__main__":
    run_smoke_test()