import pytest

from app.core.exceptions import LLMQuotaExceededError
from app.schemas.llm import LLMMessage, LLMRequest, MessageRole
from app.services.llm_service import LLMService
from tests.fakes import FakeLLMProvider


def create_request() -> LLMRequest:
    """Create a reusable LLM request for service tests."""

    return LLMRequest(
        messages=[
            LLMMessage(
                role=MessageRole.USER,
                content="Analyze the proposal.",
            )
        ]
    )


@pytest.mark.asyncio
async def test_service_calls_configured_provider() -> None:
    provider = FakeLLMProvider(
        response_content="Analysis completed.",
    )
    service = LLMService(
        provider=provider,
        max_calls_per_assessment=3,
    )

    response = await service.generate(
        assessment_id="assessment-001",
        request=create_request(),
    )

    assert response.content == "Analysis completed."
    assert service.provider_name == "fake"
    assert service.model_name == "fake-model"
    assert service.get_call_count("assessment-001") == 1
    assert service.get_remaining_calls("assessment-001") == 2


@pytest.mark.asyncio
async def test_service_tracks_assessments_independently() -> None:
    service = LLMService(
        provider=FakeLLMProvider(),
        max_calls_per_assessment=2,
    )

    await service.generate(
        assessment_id="assessment-001",
        request=create_request(),
    )
    await service.generate(
        assessment_id="assessment-002",
        request=create_request(),
    )

    assert service.get_call_count("assessment-001") == 1
    assert service.get_call_count("assessment-002") == 1
    assert service.get_remaining_calls("assessment-001") == 1
    assert service.get_remaining_calls("assessment-002") == 1


@pytest.mark.asyncio
async def test_service_blocks_calls_after_limit() -> None:
    service = LLMService(
        provider=FakeLLMProvider(),
        max_calls_per_assessment=1,
    )

    await service.generate(
        assessment_id="assessment-001",
        request=create_request(),
    )

    with pytest.raises(
        LLMQuotaExceededError,
        match="LLM call limit reached",
    ):
        await service.generate(
            assessment_id="assessment-001",
            request=create_request(),
        )

    assert service.get_call_count("assessment-001") == 1
    assert service.get_remaining_calls("assessment-001") == 0


@pytest.mark.asyncio
async def test_service_rejects_empty_assessment_id() -> None:
    service = LLMService(
        provider=FakeLLMProvider(),
        max_calls_per_assessment=2,
    )

    with pytest.raises(
        ValueError,
        match="assessment_id cannot be empty",
    ):
        await service.generate(
            assessment_id=" ",
            request=create_request(),
        )


@pytest.mark.asyncio
async def test_service_resets_assessment_quota() -> None:
    service = LLMService(
        provider=FakeLLMProvider(),
        max_calls_per_assessment=2,
    )

    await service.generate(
        assessment_id="assessment-001",
        request=create_request(),
    )

    assert service.get_call_count("assessment-001") == 1

    service.reset_assessment("assessment-001")

    assert service.get_call_count("assessment-001") == 0
    assert service.get_remaining_calls("assessment-001") == 2


def test_service_rejects_invalid_limit() -> None:
    with pytest.raises(
        ValueError,
        match="must be at least 1",
    ):
        LLMService(
            provider=FakeLLMProvider(),
            max_calls_per_assessment=0,
        )
