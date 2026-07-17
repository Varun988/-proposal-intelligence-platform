from dataclasses import dataclass
from typing import Any


@dataclass
class FakeUsageMetadata:
    """Fake Gemini token usage metadata."""

    prompt_token_count: int = 12
    candidates_token_count: int = 8
    total_token_count: int = 20


@dataclass
class FakeFinishReason:
    """Fake Gemini finish-reason enum."""

    value: str = "STOP"


@dataclass
class FakeCandidate:
    """Fake Gemini response candidate."""

    finish_reason: FakeFinishReason | None = None


@dataclass
class FakeGeminiResponse:
    """Fake response returned by the Gemini SDK."""

    text: str | None
    usage_metadata: FakeUsageMetadata | None = None
    candidates: list[FakeCandidate] | None = None


class FakeGeminiModels:
    """Fake asynchronous Gemini models client."""

    def __init__(
        self,
        response: FakeGeminiResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.received_model: str | None = None
        self.received_contents: list[Any] | None = None
        self.received_config: Any | None = None

    async def generate_content(
        self,
        *,
        model: str,
        contents: list[Any],
        config: Any,
    ) -> FakeGeminiResponse:
        self.received_model = model
        self.received_contents = contents
        self.received_config = config

        if self.error is not None:
            raise self.error

        if self.response is None:
            raise RuntimeError("Fake Gemini response was not configured.")

        return self.response


class FakeGeminiAsyncClient:
    """Fake asynchronous section of the Gemini SDK."""

    def __init__(
        self,
        models: FakeGeminiModels,
    ) -> None:
        self.models = models


class FakeGeminiClient:
    """Fake Gemini client matching the SDK interface used by the provider."""

    def __init__(
        self,
        models: FakeGeminiModels,
    ) -> None:
        self.aio = FakeGeminiAsyncClient(models)
