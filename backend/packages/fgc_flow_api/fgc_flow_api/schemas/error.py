"""Standard error response schema for consistent error formatting."""
from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response returned by all endpoints.

    Every exception handler produces this shape:
    {
        "detail": "Human-readable error message",
        "error_code": "machine-readable-error-code",
        "extra": { ... }  # optional context
    }
    """
    detail: str
    error_code: str = "internal-error"
    extra: dict[str, Any] | None = None
