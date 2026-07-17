import pytest

from app.core.exceptions import (
    ToolExecutionError,
    ToolInputValidationError,
)
from app.tools.schemas import ToolStatus
from tests.tool_fakes import (
    EchoTool,
    FailingTool,
)


def test_tool_returns_normalized_success_result() -> None:
    tool = EchoTool()

    result = tool.run(
        payload={
            "message": "Analyze proposal",
        },
        metadata={
            "assessment_id": "assessment-001",
        },
    )

    assert result.tool_name == "echo"
    assert result.status is ToolStatus.SUCCESS
    assert result.succeeded
    assert result.output == {
        "echoed_message": "Analyze proposal",
        "message_length": 16,
    }
    assert result.metadata["assessment_id"] == "assessment-001"
    assert result.execution_time_ms >= 0


def test_tool_exposes_definition() -> None:
    tool = EchoTool()

    definition = tool.get_definition()

    assert definition.name == "echo"
    assert "message" in definition.input_schema["properties"]
    assert "echoed_message" in definition.output_schema["properties"]
    assert definition.allowed_agents == (
        "orchestrator",
        "proposal-analysis",
    )


def test_tool_rejects_invalid_input() -> None:
    tool = EchoTool()

    with pytest.raises(
        ToolInputValidationError,
        match="Invalid input",
    ):
        tool.run(
            payload={
                "message": "",
            }
        )


def test_tool_normalizes_execution_failure() -> None:
    tool = FailingTool()

    with pytest.raises(
        ToolExecutionError,
        match="execution failed",
    ):
        tool.run(
            payload={
                "message": "Synthetic message",
            }
        )
