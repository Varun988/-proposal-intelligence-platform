import pytest

from app.core.exceptions import LLMConfigurationError
from app.llm.factory import LLMProviderFactory
from tests.fakes import FakeLLMProvider


def test_factory_creates_registered_provider() -> None:
    factory = LLMProviderFactory()
    factory.register("fake", FakeLLMProvider)

    provider = factory.create("fake")

    assert isinstance(provider, FakeLLMProvider)
    assert provider.provider_name == "fake"


def test_factory_normalizes_provider_name() -> None:
    factory = LLMProviderFactory()
    factory.register("  FAKE  ", FakeLLMProvider)

    provider = factory.create(" Fake ")

    assert provider.provider_name == "fake"
    assert factory.available_providers() == ("fake",)


def test_factory_rejects_duplicate_provider() -> None:
    factory = LLMProviderFactory()
    factory.register("fake", FakeLLMProvider)

    with pytest.raises(
        LLMConfigurationError,
        match="already registered",
    ):
        factory.register("FAKE", FakeLLMProvider)


def test_factory_rejects_unknown_provider() -> None:
    factory = LLMProviderFactory()
    factory.register("fake", FakeLLMProvider)

    with pytest.raises(
        LLMConfigurationError,
        match="Unsupported LLM provider",
    ):
        factory.create("gemini")


def test_factory_rejects_empty_provider_name() -> None:
    factory = LLMProviderFactory()

    with pytest.raises(
        LLMConfigurationError,
        match="cannot be empty",
    ):
        factory.create(" ")
