from abc import ABC, abstractmethod
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.exceptions import (
    ToolExecutionError,
    ToolInputValidationError,
)
from app.tools.schemas import (
    ToolDefinition,
    ToolExecutionResult,
    ToolStatus,
)


class BaseTool(ABC):
    """Base contract implemented by every agent-accessible tool."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique tool name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a human-readable tool description."""

    @property
    @abstractmethod
    def input_model(self) -> type:
        """Return the Pydantic input model used by the tool."""

    @property
    @abstractmethod
    def output_model(self) -> type:
        """Return the Pydantic output model returned by the tool."""

    @property
    def allowed_agents(self) -> tuple[str, ...]:
        """Return agents permitted to use the tool.

        An empty tuple means that access must be decided by the
        application before the tool is exposed.
        """

        return ()

    @abstractmethod
    def execute(
        self,
        tool_input: BaseModel,
    ) -> BaseModel:
        """Execute the tool using validated input."""

    def get_definition(self) -> ToolDefinition:
        """Return metadata and schemas describing the tool."""

        return ToolDefinition(
            name=self.name,
            description=self.description,
            allowed_agents=self.allowed_agents,
            input_schema=self.input_model.model_json_schema(),
            output_schema=self.output_model.model_json_schema(),
        )

    def run(
        self,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> ToolExecutionResult:
        """Validate input, execute the tool, and normalize the result."""

        started_at = perf_counter()

        try:
            validated_input = self.input_model.model_validate(
                payload,
            )
        except ValidationError as error:
            raise ToolInputValidationError(
                f"Invalid input for tool '{self.name}'."
            ) from error

        try:
            raw_output = self.execute(validated_input)
            validated_output = self.output_model.model_validate(
                raw_output,
            )
        except ToolInputValidationError:
            raise
        except Exception as error:
            raise ToolExecutionError(
                f"Tool '{self.name}' execution failed."
            ) from error

        return ToolExecutionResult(
            tool_name=self.name,
            status=ToolStatus.SUCCESS,
            output=validated_output.model_dump(mode="json"),
            execution_time_ms=self._elapsed_ms(started_at),
            metadata=metadata or {},
        )

    @staticmethod
    def _elapsed_ms(
        started_at: float,
    ) -> float:
        """Return elapsed execution time in milliseconds."""

        return max(
            (perf_counter() - started_at) * 1_000,
            0.0,
        )