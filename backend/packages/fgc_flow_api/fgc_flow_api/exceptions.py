"""Custom exceptions for fgc_flow_api with structured error codes."""

from typing import Any


class FGCFlowException(Exception):
    """Base exception for all fgc_flow_api errors."""

    def __init__(
        self,
        detail: str,
        error_code: str = "internal-error",
        status_code: int = 500,
        extra: dict[str, Any] | None = None,
    ):
        self.detail = detail
        self.error_code = error_code
        self.status_code = status_code
        self.extra = extra or {}
        super().__init__(self.detail)


class NotFoundException(FGCFlowException):
    """Resource not found."""

    def __init__(self, detail: str = "Resource not found", error_code: str = "not-found"):
        super().__init__(detail=detail, error_code=error_code, status_code=404)


class UnauthorizedException(FGCFlowException):
    """Authentication failure."""

    def __init__(
        self, detail: str = "Not authenticated", error_code: str = "auth/unauthorized"
    ):
        super().__init__(detail=detail, error_code=error_code, status_code=401)


class ForbiddenException(FGCFlowException):
    """Authorization failure."""

    def __init__(
        self, detail: str = "Permission denied", error_code: str = "auth/forbidden"
    ):
        super().__init__(detail=detail, error_code=error_code, status_code=403)


class ConflictException(FGCFlowException):
    """Resource conflict."""

    def __init__(self, detail: str = "Resource conflict", error_code: str = "conflict"):
        super().__init__(detail=detail, error_code=error_code, status_code=409)
