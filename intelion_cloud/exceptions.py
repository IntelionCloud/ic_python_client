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

    @property
    def reason(self) -> Optional[str]:
        """Machine-readable rejection label, when the server sent one.

        ``POST cloud-servers/`` puts ``reason`` next to ``detail`` in its 400
        and 409 bodies (``ServerCreateRejectReason`` values: ``validation``,
        ``cpu_limit``, ``queue_disabled``, ``internal_error``). Branch on this,
        not on the Russian ``detail`` text, which changes with copywriting.
        ``None`` for bodies without the key (DRF validation errors included).
        """
        if isinstance(self.response_body, dict):
            value = self.response_body.get("reason")
            if isinstance(value, str) and value:
                return value
        return None

    @property
    def error_code(self) -> Optional[str]:
        """Machine-readable ``error_code`` of term and disk refusals, when present.

        The term guards on the server answer with
        ``{"error_code", "message", "detail"}`` (see
        :class:`~intelion_cloud.constants.TermConflictCode`). Branch on this,
        not on the Russian message. The disk order of ``migrate(ssd_count=)``
        reports its codes here too (``change_one_at_a_time``, ``not_draft``,
        ``disk_operation_pending``, ``feature_disabled``). ``None`` for bodies
        without the key.
        """
        if isinstance(self.response_body, dict):
            value = self.response_body.get("error_code")
            if isinstance(value, str) and value:
                return value
        return None

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
    """409 Conflict: the request clashes with the server's current state.

    Several unrelated causes share this status, tell them apart by the body:

    * the server is busy with another operation (plain ``detail``);
    * queueing for a scarce GPU is forbidden: :attr:`reason` is
      ``"queue_disabled"``, ``response_body`` carries ``suggested_alternative``;
    * the rental term forbids the action: :attr:`error_code` is one of the
      :class:`~intelion_cloud.constants.TermConflictCode` values (or another
      term code), ``str(exc)`` is the server's ``message`` for the user.
      ``update(is_auto_renewal=True)`` under a running confirmed term gives
      ``AUTO_RENEWAL_CONSENT_REQUIRED``; a start during a term renewal gives
      ``TERM_RENEWAL_IN_PROGRESS``.
    """


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
