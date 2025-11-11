from typing import Optional, Dict, Any


class RAGException(Exception):
    """Custom exception for RAG application errors"""

    def __init__(
        self,
        message: str,
        error_code: str = "RAG_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(RAGException):
    """Validation error"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class AuthenticationError(RAGException):
    """Authentication error"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401
        )


class AuthorizationError(RAGException):
    """Authorization error"""

    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403
        )


class NotFoundError(RAGException):
    """Resource not found error"""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=404
        )


class ConflictError(RAGException):
    """Resource conflict error"""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=409
        )


class RateLimitError(RAGException):
    """Rate limit exceeded error"""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429
        )


class ExternalServiceError(RAGException):
    """External service error (OpenAI, Pinecone, etc.)"""

    def __init__(
        self,
        message: str,
        service: str,
        status_code: int = 502,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=f"EXTERNAL_SERVICE_ERROR_{service.upper()}",
            status_code=status_code,
            details=details
        )
        self.service = service


class DocumentProcessingError(RAGException):
    """Document processing error"""

    def __init__(
        self,
        message: str,
        document_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="DOCUMENT_PROCESSING_ERROR",
            status_code=422,
            details=details
        )
        self.document_id = document_id


class EmbeddingError(RAGException):
    """Embedding generation error"""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="EMBEDDING_ERROR",
            status_code=502,
            details=details
        )


class RetrievalError(RAGException):
    """Vector retrieval error"""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="RETRIEVAL_ERROR",
            status_code=502,
            details=details
        )


class LLMError(RAGException):
    """LLM generation error"""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="LLM_ERROR",
            status_code=502,
            details=details
        )