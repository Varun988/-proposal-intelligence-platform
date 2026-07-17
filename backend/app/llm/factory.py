from collections.abc import Callable

from app.core.exceptions import LLMConfigurationError
from app.llm.base import BaseLLMProvider

ProviderBuilder = Callable[[], BaseLLMProvider]


class LLMProviderFactory:
    """Create configured LLM providers from registered builders."""

    def __init__(self) -> None:
        self._builders: dict[str, ProviderBuilder] = {}

    def register(
        self,
        provider_name: str,
        builder: ProviderBuilder,
    ) -> None:
        """Register a provider builder under a normalized name."""

        normalized_name = self._normalize_name(provider_name)

        if normalized_name in self._builders:
            raise LLMConfigurationError(
                f"LLM provider '{normalized_name}' is already registered."
            )

        self._builders[normalized_name] = builder

    def create(self, provider_name: str) -> BaseLLMProvider:
        """Create a registered LLM provider."""

        normalized_name = self._normalize_name(provider_name)
        builder = self._builders.get(normalized_name)

        if builder is None:
            available_providers = sorted(self._builders)
            available_text = ", ".join(available_providers) or "none"

            raise LLMConfigurationError(
                f"Unsupported LLM provider '{normalized_name}'. "
                f"Available providers: {available_text}."
            )

        return builder()

    def available_providers(self) -> tuple[str, ...]:
        """Return registered provider names in stable order."""

        return tuple(sorted(self._builders))

    @staticmethod
    def _normalize_name(provider_name: str) -> str:
        normalized_name = provider_name.strip().lower()

        if not normalized_name:
            raise LLMConfigurationError(
                "LLM provider name cannot be empty."
            )

        return normalized_name