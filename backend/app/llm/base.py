from abc import ABC, abstractmethod

from app.schemas.llm import LLMRequest, LLMResponse


class BaseLLMProvider(ABC):
    """Contract implemented by every supported LLM provider."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the unique provider name."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the configured model name."""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a normalized response for the supplied request."""
