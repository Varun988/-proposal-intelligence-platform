class ApplicationError(Exception):
    """Base exception for application-specific errors."""


class LLMError(ApplicationError):
    """Base exception for LLM-related failures."""


class LLMConfigurationError(LLMError):
    """Raised when an LLM provider is incorrectly configured."""


class LLMProviderError(LLMError):
    """Raised when an LLM provider request fails."""


class LLMQuotaExceededError(LLMError):
    """Raised when an application-defined LLM quota is exceeded."""


class LLMResponseValidationError(LLMError):
    """Raised when an LLM response does not match the expected structure."""
