from pydantic import BaseModel, Field

from app.tools.base import BaseTool


class EchoToolInput(BaseModel):
    """Input accepted by the fake echo tool."""

    message: str = Field(min_length=1)


class EchoToolOutput(BaseModel):
    """Output returned by the fake echo tool."""

    echoed_message: str
    message_length: int = Field(ge=1)


class EchoTool(BaseTool):
    """Deterministic tool used only by unit tests."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Return a supplied message and its length."

    @property
    def input_model(self) -> type:
        return EchoToolInput

    @property
    def output_model(self) -> type:
        return EchoToolOutput

    @property
    def allowed_agents(self) -> tuple[str, ...]:
        return (
            "orchestrator",
            "proposal-analysis",
        )

    def execute(
        self,
        tool_input: BaseModel,
    ) -> BaseModel:
        validated_input = EchoToolInput.model_validate(
            tool_input,
        )

        return EchoToolOutput(
            echoed_message=validated_input.message,
            message_length=len(validated_input.message),
        )


class FailingTool(EchoTool):
    """Fake tool that deliberately raises during execution."""

    @property
    def name(self) -> str:
        return "failing-tool"

    def execute(
        self,
        tool_input: BaseModel,
    ) -> BaseModel:
        raise RuntimeError("Synthetic tool failure.")
