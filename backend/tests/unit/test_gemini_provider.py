import pytest

from app.core.exceptions import (
    LLMConfigurationError,
    LLMProviderError,
    LLMResponseValidationError,
)
from app.llm.providers.gemini import GeminiProvider
from app.schemas.llm import (
    LLMMessage,
    LLMRequest,
    MessageRole,
)
from tests.gemini_fakes import (
    FakeCandidate,
    FakeFinishReason,
    FakeGeminiClient,
    FakeGeminiModels,
    FakeGeminiResponse,
    FakeUsageMetadata,
)


def create_provider(
    response: FakeGeminiResponse | None = None,
    error: Exception | None = None,
) -> tuple[GeminiProvider, FakeGeminiModels]:
    """Create a Gemini provider backed by a fake SDK client."""

    models = FakeGeminiModels(
        response=response,
        error=error,
    )
    client = FakeGeminiClient(models)

    provider = GeminiProvider(
        api_key="test-api-key",
        model_name="test-gemini-model",
        client=client,
    )

    return provider, models


def create_request(
    response_schema: dict[str, object] | None = None,
) -> LLMRequest:
    """Create a reusable Gemini provider request."""

    return LLMRequest(
        messages=[
            LLMMessage(
                role=MessageRole.SYSTEM,
                content="Analyze proposals using evidence only.",
            ),
            LLMMessage(
                role=MessageRole.USER,
                content="Identify missing delivery information.",
            ),
        ],
        temperature=0.0,
        max_output_tokens=1024,
        response_schema=response_schema,
    )


@pytest.mark.asyncio
async def test_provider_returns_normalized_response() -> None:
    response = FakeGeminiResponse(
        text="Delivery timeline is missing.",
        usage_metadata=FakeUsageMetadata(
            prompt_token_count=15,
            candidates_token_count=7,
            total_token_count=22,
        ),
        candidates=[
            FakeCandidate(
                finish_reason=FakeFinishReason(
                    value="STOP",
                )
            )
        ],
    )
    provider, models = create_provider(response=response)

    result = await provider.generate(create_request())

    assert result.content == "Delivery timeline is missing."
    assert result.provider == "gemini"
    assert result.model == "test-gemini-model"
    assert result.usage.input_tokens == 15
    assert result.usage.output_tokens == 7
    assert result.usage.total_tokens == 22
    assert result.finish_reason == "stop"
    assert models.received_model == "test-gemini-model"


@pytest.mark.asyncio
async def test_provider_builds_system_instruction() -> None:
    response = FakeGeminiResponse(
        text="Analysis completed.",
    )
    provider, models = create_provider(response=response)

    await provider.generate(create_request())

    assert models.received_config.system_instruction == ("Analyze proposals using evidence only.")
    assert len(models.received_contents or []) == 1
    assert models.received_contents[0].role == "user"


@pytest.mark.asyncio
async def test_provider_parses_structured_response() -> None:
    response = FakeGeminiResponse(
        text='{"status": "completed", "risk_count": 2}',
    )
    provider, models = create_provider(response=response)

    result = await provider.generate(
        create_request(
            response_schema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                    },
                    "risk_count": {
                        "type": "integer",
                    },
                },
                "required": [
                    "status",
                    "risk_count",
                ],
            }
        )
    )

    assert result.structured_data == {
        "status": "completed",
        "risk_count": 2,
    }
    assert models.received_config.response_mime_type == "application/json"


@pytest.mark.asyncio
async def test_provider_rejects_invalid_structured_json() -> None:
    response = FakeGeminiResponse(
        text="This is not JSON.",
    )
    provider, _ = create_provider(response=response)

    with pytest.raises(
        LLMResponseValidationError,
        match="invalid structured JSON",
    ):
        await provider.generate(
            create_request(
                response_schema={
                    "type": "object",
                }
            )
        )


@pytest.mark.asyncio
async def test_provider_rejects_empty_response() -> None:
    response = FakeGeminiResponse(
        text=" ",
    )
    provider, _ = create_provider(response=response)

    with pytest.raises(
        LLMResponseValidationError,
        match="empty response",
    ):
        await provider.generate(create_request())


@pytest.mark.asyncio
async def test_provider_translates_sdk_error() -> None:
    provider, _ = create_provider(
        error=RuntimeError("Provider unavailable."),
    )

    with pytest.raises(
        LLMProviderError,
        match="Gemini request failed",
    ):
        await provider.generate(create_request())


def test_provider_rejects_empty_api_key() -> None:
    with pytest.raises(
        LLMConfigurationError,
        match="API key is required",
    ):
        GeminiProvider(
            api_key=" ",
            model_name="test-model",
        )


def test_provider_rejects_empty_model_name() -> None:
    with pytest.raises(
        LLMConfigurationError,
        match="model name is required",
    ):
        GeminiProvider(
            api_key="test-api-key",
            model_name=" ",
        )


@pytest.mark.asyncio
async def test_provider_requires_non_system_message() -> None:
    response = FakeGeminiResponse(
        text="Unused response.",
    )
    provider, _ = create_provider(response=response)

    request = LLMRequest(
        messages=[
            LLMMessage(
                role=MessageRole.SYSTEM,
                content="System instruction only.",
            )
        ]
    )

    with pytest.raises(
        LLMConfigurationError,
        match="non-system message",
    ):
        await provider.generate(request)
