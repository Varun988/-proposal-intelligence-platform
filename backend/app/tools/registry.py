from typing import Any

from app.core.exceptions import (
    ToolNotFoundError,
    ToolPermissionError,
    ToolRegistrationError,
)
from app.tools.base import BaseTool
from app.tools.schemas import (
    ToolDefinition,
    ToolExecutionResult,
)


class ToolRegistry:
    """Register, discover, and safely execute bounded tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(
        self,
        tool: BaseTool,
    ) -> None:
        """Register a tool using its normalized unique name."""

        normalized_name = self._normalize_name(
            tool.name,
        )

        if normalized_name in self._tools:
            raise ToolRegistrationError(f"Tool '{normalized_name}' is already registered.")

        self._tools[normalized_name] = tool

    def get(
        self,
        tool_name: str,
    ) -> BaseTool:
        """Return a registered tool."""

        normalized_name = self._normalize_name(
            tool_name,
        )
        tool = self._tools.get(normalized_name)

        if tool is None:
            raise ToolNotFoundError(f"Tool '{normalized_name}' is not registered.")

        return tool

    def execute(
        self,
        tool_name: str,
        payload: dict[str, Any],
        agent_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> ToolExecutionResult:
        """Execute a tool after validating agent access."""

        tool = self.get(tool_name)

        normalized_agent_name = self._normalize_name(
            agent_name,
        )

        self._validate_permission(
            tool=tool,
            agent_name=normalized_agent_name,
        )

        execution_metadata = {
            **(metadata or {}),
            "agent_name": normalized_agent_name,
        }

        return tool.run(
            payload=payload,
            metadata=execution_metadata,
        )

    def definitions_for_agent(
        self,
        agent_name: str,
    ) -> tuple[ToolDefinition, ...]:
        """Return definitions of tools available to an agent."""

        normalized_agent_name = self._normalize_name(
            agent_name,
        )

        definitions = [
            tool.get_definition()
            for tool in self._tools.values()
            if normalized_agent_name in tool.allowed_agents
        ]

        return tuple(
            sorted(
                definitions,
                key=lambda definition: definition.name,
            )
        )

    def registered_names(self) -> tuple[str, ...]:
        """Return registered tool names in stable order."""

        return tuple(sorted(self._tools))

    @staticmethod
    def _validate_permission(
        tool: BaseTool,
        agent_name: str,
    ) -> None:
        """Ensure the calling agent may use the tool."""

        if agent_name not in tool.allowed_agents:
            raise ToolPermissionError(
                f"Agent '{agent_name}' is not permitted to use tool '{tool.name}'."
            )

    @staticmethod
    def _normalize_name(
        value: str,
    ) -> str:
        """Normalize a tool or agent name."""

        normalized_value = value.strip().lower()

        if not normalized_value:
            raise ToolRegistrationError("Tool and agent names cannot be empty.")

        return normalized_value

