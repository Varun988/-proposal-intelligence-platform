import json
from typing import Any

from google import genai
from google.genai import types

from app.core.exceptions import (
    LLMConfigurationError,
    LLMProviderError,
    LLMResponseValidationError,
)
from app.llm.base import BaseLLMProvider
from app.schemas.llm import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
    MessageRole,
    TokenUsage,
)


class GeminiProvider(BaseLLMProvider):
    """Gemini implementation of the provider-independent LLM contract."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        client: Any | None = None,
    ) -> None:
        normalized_api_key = api_key.strip()
        normalized_model_name = model_name.strip()

        if not normalized_api_key:
            raise LLMConfigurationError(
                "Gemini API key is required.",
            )

        if not normalized_model_name:
            raise LLMConfigurationError(
                "Gemini model name is required.",
            )

        self._model_name = normalized_model_name
        self._client = client or genai.Client(
            api_key=normalized_api_key,
        )

    @property
    def provider_name(self) -> str:
        """Return the provider identifier."""

        return "gemini"

    @property
    def model_name(self) -> str:
        """Return the configured Gemini model name."""

        return self._model_name

    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """Generate and normalize a Gemini response."""

        try:
            system_instruction = self._build_system_instruction(
                request.messages,
            )
            contents = self._build_contents(request.messages)
            config = self._build_generation_config(
                request=request,
                system_instruction=system_instruction,
            )

            response = await self._client.aio.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )

            return self._normalize_response(
                response=response,
                expects_structured_output=(request.response_schema is not None),
            )
        except (
            LLMConfigurationError,
            LLMResponseValidationError,
        ):
            raise
        except Exception as error:
            raise LLMProviderError("Gemini request failed.") from error

    @staticmethod
    def _build_system_instruction(
        messages: list[LLMMessage],
    ) -> str | None:
        """Combine system messages into one Gemini instruction."""

        system_messages = [
            message.content for message in messages if message.role is MessageRole.SYSTEM
        ]

        if not system_messages:
            return None

        return "\n\n".join(system_messages)

    @staticmethod
    def _build_contents(
        messages: list[LLMMessage],
    ) -> list[types.Content]:
        """Convert provider-independent messages into Gemini content."""

        contents: list[types.Content] = []

        for message in messages:
            if message.role is MessageRole.SYSTEM:
                continue

            role = GeminiProvider._map_role(message.role)
            text = GeminiProvider._format_message_content(message)

            contents.append(
                types.Content(
                    role=role,
                    parts=[
                        types.Part.from_text(
                            text=text,
                        )
                    ],
                )
            )

        if not contents:
            raise LLMConfigurationError("At least one non-system message is required.")

        return contents

    @staticmethod
    def _map_role(role: MessageRole) -> str:
        """Map application roles to supported Gemini roles."""

        if role is MessageRole.ASSISTANT:
            return "model"

        return "user"

    @staticmethod
    def _format_message_content(
        message: LLMMessage,
    ) -> str:
        """Format special message roles for Gemini."""

        if message.role is MessageRole.TOOL:
            return f"Tool result:\n{message.content}"

        return message.content

    @staticmethod
    def _build_generation_config(
        request: LLMRequest,
        system_instruction: str | None,
    ) -> types.GenerateContentConfig:
        """Create Gemini generation configuration."""

        config_values: dict[str, Any] = {
            "temperature": request.temperature,
            "max_output_tokens": request.max_output_tokens,
        }

        if system_instruction:
            config_values["system_instruction"] = system_instruction

        if request.response_schema is not None:
            config_values["response_mime_type"] = "application/json"
            config_values["response_json_schema"] = request.response_schema

        return types.GenerateContentConfig(**config_values)

    def _normalize_response(
        self,
        response: Any,
        expects_structured_output: bool,
    ) -> LLMResponse:
        """Convert a Gemini SDK response into the shared response model."""

        content = self._extract_text(response)

        structured_data: dict[str, Any] | None = None

        if expects_structured_output:
            structured_data = self._parse_structured_content(content)

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=self.model_name,
            usage=self._extract_usage(response),
            finish_reason=self._extract_finish_reason(response),
            structured_data=structured_data,
        )

    @staticmethod
    def _extract_text(response: Any) -> str:
        """Extract and validate response text."""

        content = getattr(response, "text", None)

        if not content or not content.strip():
            raise LLMResponseValidationError("Gemini returned an empty response.")

        return content.strip()

    @staticmethod
    def _parse_structured_content(
        content: str,
    ) -> dict[str, Any]:
        """Parse a structured Gemini response."""

        try:
            parsed_content = json.loads(content)
        except json.JSONDecodeError as error:
            raise LLMResponseValidationError("Gemini returned invalid structured JSON.") from error

        if not isinstance(parsed_content, dict):
            raise LLMResponseValidationError("Gemini structured output must be a JSON object.")

        return parsed_content

    @staticmethod
    def _extract_usage(response: Any) -> TokenUsage:
        """Extract token usage from a Gemini response."""

        usage_metadata = getattr(
            response,
            "usage_metadata",
            None,
        )

        if usage_metadata is None:
            return TokenUsage()

        input_tokens = (
            getattr(
                usage_metadata,
                "prompt_token_count",
                0,
            )
            or 0
        )
        output_tokens = (
            getattr(
                usage_metadata,
                "candidates_token_count",
                0,
            )
            or 0
        )
        total_tokens = (
            getattr(
                usage_metadata,
                "total_token_count",
                0,
            )
            or input_tokens + output_tokens
        )

        return TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    @staticmethod
    def _extract_finish_reason(
        response: Any,
    ) -> str | None:
        """Extract a normalized candidate finish reason."""

        candidates = getattr(response, "candidates", None)

        if not candidates:
            return None

        finish_reason = getattr(
            candidates[0],
            "finish_reason",
            None,
        )

        if finish_reason is None:
            return None

        finish_reason_value = getattr(
            finish_reason,
            "value",
            finish_reason,
        )

        return str(finish_reason_value).lower()
