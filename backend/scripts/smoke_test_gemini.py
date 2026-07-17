import asyncio

from app.core.config import get_settings
from app.llm.providers.gemini import GeminiProvider
from app.schemas.llm import (
    LLMMessage,
    LLMRequest,
    MessageRole,
)
from app.services.llm_service import LLMService


async def run_smoke_test() -> None:
    """Run one controlled request against the configured Gemini model."""

    settings = get_settings()

    provider = GeminiProvider(
        api_key=settings.gemini_api_key,
        model_name=settings.llm_model,
    )

    llm_service = LLMService(
        provider=provider,
        max_calls_per_assessment=1,
    )

    request = LLMRequest(
        messages=[
            LLMMessage(
                role=MessageRole.SYSTEM,
                content=(
                    "You are a proposal analysis assistant. "
                    "Respond only with facts contained in the user message."
                ),
            ),
            LLMMessage(
                role=MessageRole.USER,
                content=(
                    "Synthetic proposal information: "
                    "The proposed delivery timeline is 12 months. "
                    "Return the delivery timeline in one short sentence."
                ),
            ),
        ],
        temperature=0.0,
        max_output_tokens=100,
        metadata={
            "test_type": "gemini_smoke_test",
            "data_classification": "synthetic",
        },
    )

    response = await llm_service.generate(
        assessment_id="smoke-test-001",
        request=request,
    )

    print("Gemini smoke test successful")
    print(f"Provider: {response.provider}")
    print(f"Model: {response.model}")
    print(f"Response: {response.content}")
    print(f"Input tokens: {response.usage.input_tokens}")
    print(f"Output tokens: {response.usage.output_tokens}")
    print(f"Total tokens: {response.usage.total_tokens}")
    print(f"Finish reason: {response.finish_reason}")
    print(f"Calls remaining: {llm_service.get_remaining_calls('smoke-test-001')}")


if __name__ == "__main__":
    asyncio.run(run_smoke_test())
