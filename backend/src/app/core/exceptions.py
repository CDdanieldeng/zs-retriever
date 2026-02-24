"""Application exceptions."""


class RetrieverError(Exception):
    """Base exception for Retriever Service."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(RetrieverError):
    """Resource not found."""


class ValidationError(RetrieverError):
    """Validation error."""
