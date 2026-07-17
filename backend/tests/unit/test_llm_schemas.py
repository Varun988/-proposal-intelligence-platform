import pytest
from pydantic import ValidationError

from app.schemas.llm import LLMMessage, LLMRequest, MessageRole


def test_llm_request_accepts_valid_messages() -> None:
    request = LLMRequest(
        messages=[
            LLMMessage(
                role=MessageRole.SYSTEM,
                content="Analyze the proposal.",
            ),
            LLMMessage(
                role=MessageRole.USER,
                content="Identify missing delivery information.",
            ),
        ],
        temperature=0.0,
        max_output_tokens=1024,
    )

    assert len(request.messages) == 2
    assert request.messages[0].role is MessageRole.SYSTEM
    assert request.max_output_tokens == 1024


def test_llm_request_rejects_empty_message_list() -> None:
    with pytest.raises(ValidationError):
        LLMRequest(messages=[])


def test_llm_message_rejects_empty_content() -> None:
    with pytest.raises(ValidationError):
        LLMMessage(
            role=MessageRole.USER,
            content="",
        )


def test_llm_request_rejects_invalid_temperature() -> None:
    with pytest.raises(ValidationError):
        LLMRequest(
            messages=[
                LLMMessage(
                    role=MessageRole.USER,
                    content="Analyze this proposal.",
                )
            ],
            temperature=3.0,
        )
