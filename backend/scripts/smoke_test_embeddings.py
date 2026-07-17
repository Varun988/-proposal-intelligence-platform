from app.core.config import get_settings
from app.rag.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingProvider,
)


def run_smoke_test() -> None:
    """Generate local embeddings using synthetic text."""

    settings = get_settings()

    provider = SentenceTransformerEmbeddingProvider(
        model_name=settings.embedding_model,
        normalize_embeddings=settings.normalize_embeddings,
    )

    document_vectors = provider.embed_documents(
        [
            "The delivery timeline is twelve months.",
            "The vendor provides three years of support.",
        ]
    )

    query_vector = provider.embed_query("What is the project delivery timeline?")

    print("Local embedding smoke test successful")
    print(f"Provider: {provider.provider_name}")
    print(f"Model: {provider.model_name}")
    print(f"Dimension: {provider.dimension}")
    print(f"Document vectors: {len(document_vectors)}")
    print(f"Query dimension: {query_vector.dimension}")


if __name__ == "__main__":
    run_smoke_test()
