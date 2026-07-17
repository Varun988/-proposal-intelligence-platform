from app.llm.base import BaseLLMProvider
from app.schemas.llm import LLMRequest, LLMResponse, TokenUsage


class FakeLLMProvider(BaseLLMProvider):
    """Deterministic LLM provider used by unit tests."""

    def __init__(
        self,
        response_content: str = "Test response",
        structured_data: dict[str, object] | None = None,
    ) -> None:
        self.response_content = response_content
        self.structured_data = structured_data
        self.received_requests: list[LLMRequest] = []

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake-model"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.received_requests.append(request)

        return LLMResponse(
            content=self.response_content,
            provider=self.provider_name,
            model=self.model_name,
            usage=TokenUsage(
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
            ),
            finish_reason="stop",
            structured_data=self.structured_data,
        )
