import pytest
from app.tools.registry import ToolRegistry

from app.core.exceptions import (
    ToolNotFoundError,
    ToolPermissionError,
    ToolRegistrationError,
)
from tests.tool_fakes import EchoTool


def test_registry_registers_and_returns_tool() -> None:
    registry = ToolRegistry()
    tool = EchoTool()

    registry.register(tool)

    assert registry.get("echo") is tool
    assert registry.get(" ECHO ") is tool
    assert registry.registered_names() == ("echo",)


def test_registry_executes_permitted_tool() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())

    result = registry.execute(
        tool_name="echo",
        payload={
            "message": "Proposal evidence",
        },
        agent_name="proposal-analysis",
        metadata={
            "assessment_id": "assessment-001",
        },
    )

    assert result.succeeded
    assert result.output == {
        "echoed_message": "Proposal evidence",
        "message_length": 17,
    }
    assert result.metadata["agent_name"] == ("proposal-analysis")


def test_registry_blocks_unauthorized_agent() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())

    with pytest.raises(
        ToolPermissionError,
        match="not permitted",
    ):
        registry.execute(
            tool_name="echo",
            payload={
                "message": "Restricted request",
            },
            agent_name="vendor-research",
        )


def test_registry_rejects_duplicate_tool() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())

    with pytest.raises(
        ToolRegistrationError,
        match="already registered",
    ):
        registry.register(EchoTool())


def test_registry_rejects_unknown_tool() -> None:
    registry = ToolRegistry()

    with pytest.raises(
        ToolNotFoundError,
        match="not registered",
    ):
        registry.get("missing-tool")


def test_registry_returns_definitions_for_agent() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())

    definitions = registry.definitions_for_agent(
        "proposal-analysis",
    )

    assert len(definitions) == 1
    assert definitions[0].name == "echo"


def test_registry_hides_tools_from_unauthorized_agent() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())

    definitions = registry.definitions_for_agent(
        "vendor-research",
    )

    assert definitions == ()
