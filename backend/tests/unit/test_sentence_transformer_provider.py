import pytest

from app.core.exceptions import (
    EmbeddingConfigurationError,
    EmbeddingDimensionError,
    EmbeddingProviderError,
)
from app.rag.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingProvider,
)
from tests.sentence_transformer_fakes import (
    FailingSentenceTransformerModel,
    FakeSentenceTransformerModel,
    InvalidDimensionSentenceTransformerModel,
)


def create_provider(
    model: FakeSentenceTransformerModel | None = None,
) -> SentenceTransformerEmbeddingProvider:
    """Create a provider using a fake local model."""

    return SentenceTransformerEmbeddingProvider(
        model_name="fake-sentence-transformer",
        model=model or FakeSentenceTransformerModel(),
    )


def test_provider_exposes_configuration() -> None:
    provider = create_provider(
        FakeSentenceTransformerModel(
            dimension=5,
        )
    )

    assert provider.provider_name == "sentence-transformers"
    assert provider.model_name == "fake-sentence-transformer"
    assert provider.dimension == 5


def test_provider_embeds_documents() -> None:
    model = FakeSentenceTransformerModel(
        dimension=3,
    )
    provider = create_provider(model)

    vectors = provider.embed_documents(
        [
            "Delivery timeline is twelve months.",
            "Support period is three years.",
        ]
    )

    assert len(vectors) == 2
    assert vectors[0].dimension == 3
    assert vectors[1].dimension == 3

    assert model.received_texts == [
        "Delivery timeline is twelve months.",
        "Support period is three years.",
    ]
    assert model.received_convert_to_numpy is True
    assert model.received_normalize_embeddings is True
    assert model.received_show_progress_bar is False


def test_provider_embeds_query() -> None:
    model = FakeSentenceTransformerModel(
        dimension=3,
    )
    provider = create_provider(model)

    vector = provider.embed_query("What is the delivery timeline?")

    assert vector.dimension == 3
    assert model.received_texts == ["What is the delivery timeline?"]


def test_provider_handles_empty_document_collection() -> None:
    provider = create_provider()

    vectors = provider.embed_documents([])

    assert vectors == []


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "\n",
    ],
)
def test_provider_rejects_empty_text(
    text: str,
) -> None:
    provider = create_provider()

    with pytest.raises(
        ValueError,
        match="Text to embed cannot be empty",
    ):
        provider.embed_query(text)


def test_provider_rejects_empty_model_name() -> None:
    with pytest.raises(
        EmbeddingConfigurationError,
        match="model name is required",
    ):
        SentenceTransformerEmbeddingProvider(
            model_name=" ",
            model=FakeSentenceTransformerModel(),
        )


def test_provider_translates_encoding_failure() -> None:
    provider = create_provider(
        FailingSentenceTransformerModel(),
    )

    with pytest.raises(
        EmbeddingProviderError,
        match="encoding failed",
    ):
        provider.embed_query(
            "Synthetic query.",
        )


def test_provider_rejects_invalid_vector_dimension() -> None:
    provider = create_provider(
        InvalidDimensionSentenceTransformerModel(
            dimension=3,
        )
    )

    with pytest.raises(
        EmbeddingDimensionError,
        match="does not match",
    ):
        provider.embed_query(
            "Synthetic query.",
        )
