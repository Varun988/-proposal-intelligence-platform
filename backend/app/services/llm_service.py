from app.core.exceptions import LLMQuotaExceededError
from app.llm.base import BaseLLMProvider
from app.schemas.llm import LLMRequest, LLMResponse


class LLMService:
    """Coordinate provider calls and enforce application-level limits."""

    def __init__(
        self,
        provider: BaseLLMProvider,
        max_calls_per_assessment: int,
    ) -> None:
        if max_calls_per_assessment < 1:
            raise ValueError("max_calls_per_assessment must be at least 1.")

        self._provider = provider
        self._max_calls_per_assessment = max_calls_per_assessment
        self._call_counts: dict[str, int] = {}

    @property
    def provider_name(self) -> str:
        """Return the active provider name."""

        return self._provider.provider_name

    @property
    def model_name(self) -> str:
        """Return the active model name."""

        return self._provider.model_name

    async def generate(
        self,
        assessment_id: str,
        request: LLMRequest,
    ) -> LLMResponse:
        """Generate an LLM response within assessment quota limits."""

        normalized_assessment_id = assessment_id.strip()

        if not normalized_assessment_id:
            raise ValueError("assessment_id cannot be empty.")

        current_count = self.get_call_count(normalized_assessment_id)

        if current_count >= self._max_calls_per_assessment:
            raise LLMQuotaExceededError(
                "LLM call limit reached for assessment "
                f"'{normalized_assessment_id}'. "
                f"Maximum allowed calls: "
                f"{self._max_calls_per_assessment}."
            )

        self._call_counts[normalized_assessment_id] = current_count + 1

        return await self._provider.generate(request)

    def get_call_count(self, assessment_id: str) -> int:
        """Return the number of attempted calls for an assessment."""

        return self._call_counts.get(assessment_id.strip(), 0)

    def get_remaining_calls(self, assessment_id: str) -> int:
        """Return remaining allowed calls for an assessment."""

        used_calls = self.get_call_count(assessment_id)

        return max(
            self._max_calls_per_assessment - used_calls,
            0,
        )

    def reset_assessment(self, assessment_id: str) -> None:
        """Clear in-memory quota state for an assessment."""

        self._call_counts.pop(assessment_id.strip(), None)
