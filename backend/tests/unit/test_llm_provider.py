import pytest

from app.schemas.llm import LLMMessage, LLMRequest, MessageRole
from tests.fakes import FakeLLMProvider


@pytest.mark.asyncio
async def test_fake_provider_returns_normalized_response() -> None:
    provider = FakeLLMProvider(
        response_content="Proposal analysis completed.",
        structured_data={"status": "completed"},
    )

    request = LLMRequest(
        messages=[
            LLMMessage(
                role=MessageRole.USER,
                content="Analyze the proposal.",
            )
        ]
    )

    response = await provider.generate(request)

    assert response.content == "Proposal analysis completed."
    assert response.provider == "fake"
    assert response.model == "fake-model"
    assert response.structured_data == {"status": "completed"}
    assert response.usage.total_tokens == 15


@pytest.mark.asyncio
async def test_fake_provider_records_received_request() -> None:
    provider = FakeLLMProvider()

    request = LLMRequest(
        messages=[
            LLMMessage(
                role=MessageRole.USER,
                content="Find proposal risks.",
            )
        ],
        metadata={"assessment_id": "assessment-001"},
    )

    await provider.generate(request)

    assert len(provider.received_requests) == 1
    assert provider.received_requests[0] == request
    assert provider.received_requests[0].metadata["assessment_id"] == "assessment-001"
