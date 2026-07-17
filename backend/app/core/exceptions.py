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


class DocumentError(ApplicationError):
    """Base exception for document-processing failures."""


class DocumentNotFoundError(DocumentError):
    """Raised when a requested source document does not exist."""


class UnsupportedDocumentError(DocumentError):
    """Raised when the supplied document type is unsupported."""


class DocumentExtractionError(DocumentError):
    """Raised when content cannot be extracted from a document."""


class EncryptedDocumentError(DocumentExtractionError):
    """Raised when an encrypted document cannot be opened."""