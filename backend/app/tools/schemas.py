from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ToolStatus(StrEnum):
    """Possible outcomes of a tool execution."""

    SUCCESS = "success"
    FAILED = "failed"


class ToolDefinition(BaseModel):
    """Metadata describing an agent-accessible tool."""

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    allowed_agents: tuple[str, ...] = ()
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


class ToolExecutionResult(BaseModel):
    """Normalized result returned by every tool execution."""

    tool_name: str = Field(min_length=1)
    status: ToolStatus
    output: dict[str, Any] | None = None
    error_type: str | None = None
    error_message: str | None = None
    execution_time_ms: float = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        """Return whether the tool execution succeeded."""

        return self.status is ToolStatus.SUCCESS
