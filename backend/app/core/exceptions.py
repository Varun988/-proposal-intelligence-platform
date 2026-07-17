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


class DocumentParserRegistrationError(DocumentError):
    """Raised when document parser registration is invalid."""


class DocumentChunkingError(DocumentError):
    """Raised when document content cannot be chunked."""


class InvalidChunkingConfigurationError(DocumentChunkingError):
    """Raised when text-chunking configuration is invalid."""


class EmbeddingError(ApplicationError):
    """Base exception for embedding-related failures."""


class EmbeddingConfigurationError(EmbeddingError):
    """Raised when an embedding provider is incorrectly configured."""


class EmbeddingProviderError(EmbeddingError):
    """Raised when an embedding provider cannot generate vectors."""


class EmbeddingDimensionError(EmbeddingError):
    """Raised when generated embedding dimensions are inconsistent."""


class VectorStoreError(ApplicationError):
    """Base exception for vector-store failures."""


class VectorStoreConfigurationError(VectorStoreError):
    """Raised when a vector store is incorrectly configured."""


class VectorDimensionMismatchError(VectorStoreError):
    """Raised when vector dimensions do not match the index."""


class EmptyVectorStoreError(VectorStoreError):
    """Raised when a search is attempted against an empty vector store."""


class RetrievalError(ApplicationError):
    """Base exception for retrieval-pipeline failures."""


class DeduplicationConfigurationError(RetrievalError):
    """Raised when deduplication configuration is invalid."""


class RerankingConfigurationError(RetrievalError):
    """Raised when reranking configuration is invalid."""
