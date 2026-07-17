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


class RetrievalConfigurationError(RetrievalError):
    """Raised when retrieval-pipeline configuration is invalid."""


class ToolError(ApplicationError):
    """Base exception for tool-related failures."""


class ToolConfigurationError(ToolError):
    """Raised when a tool is incorrectly configured."""


class ToolRegistrationError(ToolError):
    """Raised when tool registration is invalid."""


class ToolNotFoundError(ToolError):
    """Raised when a requested tool is not registered."""


class ToolPermissionError(ToolError):
    """Raised when an agent is not permitted to use a tool."""


class ToolInputValidationError(ToolError):
    """Raised when tool input does not match its schema."""


class ToolExecutionError(ToolError):
    """Raised when a tool fails during execution."""


class AgentError(ApplicationError):
    """Base exception for agent-related failures."""


class AgentConfigurationError(AgentError):
    """Raised when an agent is incorrectly configured."""


class AgentExecutionError(AgentError):
    """Raised when an agent cannot complete its task."""


class AgentToolLimitError(AgentExecutionError):
    """Raised when an agent exceeds its permitted tool-call limit."""


class AgentOutputValidationError(AgentExecutionError):
    """Raised when an agent returns invalid structured output."""


class EvaluationError(ApplicationError):
    """Base exception for evaluation-related failures."""


class EvaluationConfigurationError(EvaluationError):
    """Raised when evaluators or release gates are misconfigured."""


class EvaluationExecutionError(EvaluationError):
    """Raised when an evaluator cannot complete its evaluation."""


class AssessmentError(ApplicationError):
    """Base exception for assessment operations."""


class AssessmentNotFoundError(AssessmentError):
    """Raised when an assessment cannot be found."""


class AssessmentConflictError(AssessmentError):
    """Raised when an assessment operation conflicts with its state."""


class AssessmentExecutionError(AssessmentError):
    """Raised when an assessment workflow cannot be executed."""
