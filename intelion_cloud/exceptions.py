"""Exception hierarchy for the Intelion Cloud client."""

from typing import Any, Dict, Optional

__all__ = [
    "IntelionCloudError",
    "APIError",
    "AuthenticationError",
    "PaymentRequiredError",
    "ForbiddenError",
    "NotFoundError",
    "ConflictError",
    "RateLimitError",
    "ValidationError",
    "ServerError",
    "ConnectionError",
]


class IntelionCloudError(Exception):
    """Base exception for all Intelion Cloud client errors."""


class APIError(IntelionCloudError):
    """Error returned by the Intelion Cloud API."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        response_body: Any = None,
    ) -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(status_code={self.status_code}, message={str(self)!r})"


class AuthenticationError(APIError):
    """401 Unauthorized — invalid or missing API token."""


class PaymentRequiredError(APIError):
    """402 Payment Required — AI API self-serve gate not open yet.

    Raised by ``inference_api_keys.request_access()``. ``response_body``
    carries ``shortfall_rub_cents`` — how much more balance is needed.
    """


class ForbiddenError(APIError):
    """403 Forbidden — insufficient permissions.

    For AI API endpoints specifically, ``response_body`` may carry a
    machine-readable gate: ``{"code": "aiapi_access_not_granted", "how_to",
    "threshold_rub_cents"}`` — see ``inference_api_keys.access_status()``.
    """


class NotFoundError(APIError):
    """404 Not Found — resource does not exist."""


class ConflictError(APIError):
    """409 Conflict — server is busy with another operation."""


class RateLimitError(APIError):
    """429 Too Many Requests — rate limit exceeded."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 429,
        response_body: Any = None,
        retry_after: Optional[float] = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, status_code=status_code, response_body=response_body)


class ValidationError(APIError):
    """400 Bad Request — validation failed with field-level errors."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        response_body: Any = None,
        field_errors: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.field_errors = field_errors or {}
        super().__init__(message, status_code=status_code, response_body=response_body)


class ServerError(APIError):
    """5xx Server Error — Intelion Cloud API server error."""


class ConnectionError(IntelionCloudError):
    """Network-level error (connection refused, timeout, DNS failure)."""
