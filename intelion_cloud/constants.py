"""Enumerations and constants matching the Intelion Cloud API."""

from enum import IntEnum

__all__ = [
    "ServerStatus",
    "ServerState",
    "PricePlan",
    "BillingPeriod",
    "OSType",
    "TermState",
    "ServerCreateRejectReason",
    "TermConflictCode",
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT",
    "DEFAULT_CONNECT_TIMEOUT",
]

DEFAULT_BASE_URL = "https://intelion.cloud"
DEFAULT_TIMEOUT = 30.0
DEFAULT_CONNECT_TIMEOUT = 10.0


class ServerStatus(IntEnum):
    """Server status codes returned by the API."""

    ERROR = -4
    DELETED = -3
    REQUESTED = -2
    PAUSED = -1
    PAUSING = 0
    START = 1
    ACTIVE = 2
    PREPARING = 3


class ServerState(IntEnum):
    """Server state codes indicating current operation."""

    IDLE = 0
    STARTING = 100
    SHELVING = 200
    MIGRATING_SHELVING = 301
    MIGRATING_SNAPSHOTTING = 302
    MIGRATING_DELETING = 303
    MIGRATING_CREATING = 304
    CLONING = 400
    QUEUED = 500
    AWAITING_PASSWORD = 600
    MAINTENANCE = 700
    CLEANUP_IN_PROGRESS = 800
    REINSTALLING = 900
    # On the way to cold storage; NOT yet in storage (``cold_storage`` is still None).
    COLD_MOVING = 950
    COLD_STORAGE = 1000
    # Cold storage with zero balance: the volume is deleted at ``cold_grace_deadline``.
    COLD_GRACE = 1100


class PricePlan(IntEnum):
    """Billing plan options for server configurations."""

    POSTPAID_QUARTER = -3
    POSTPAID_MONTHLY = -1
    HOURLY = 0
    MONTHLY = 1
    QUARTERLY = 3
    SEMIANNUAL = 6
    ANNUAL = 12


class BillingPeriod(IntEnum):
    """Billing period types used in usage acts."""

    HOURLY = 0
    MONTHLY = 30
    MONTHLY_ALIGNED = 31


class OSType:
    """Operating system type identifiers."""

    WINDOWS = "win"
    LINUX = "lin"


class TermState:
    """Rental-term state codes returned in ``CloudServer.term_state``.

    Computed on the server from the ``term_*`` snapshot fields; branch on the
    code, do not re-derive the state from the dates client-side.
    """

    NOT_TERM_PLAN = "not_term_plan"
    """Hourly or postpaid plan: there is no commitment at all."""
    ACTIVE = "active"
    """The term is running and the snapshot applies to the current plan."""
    PENDING_CONSENT = "pending_consent"
    """Conditions accepted, snapshot written, dates not set yet: the first usage act starts the term."""
    GRANDFATHERED = "grandfathered"
    """Legacy configuration without dates and without consent; dates are filled on start, no gates."""
    LEGACY_EXPIRED = "legacy_expired"
    """Legacy term expired without consent: re-armed on start for the same length with its own discount."""
    CONFIRMED_EXPIRED = "confirmed_expired"
    """A confirmed term ended: no discount until a new consent is given."""


class ServerCreateRejectReason:
    """Machine-readable labels in ``reason`` of ``POST cloud-servers/`` refusals.

    Read them through :attr:`intelion_cloud.exceptions.APIError.reason`. Values
    mirror ``user_panel.consts.ServerCreateRejectReason`` on the server
    (MIAN-412); the key is additive next to ``detail``.
    """

    VALIDATION = "validation"
    """The request did not pass serializer validation (400)."""
    CPU_LIMIT = "cpu_limit"
    """The account's limit of GPU-less servers is exhausted (400)."""
    QUEUE_DISABLED = "queue_disabled"
    """Queueing for this GPU is forbidden; ``suggested_alternative`` is offered (409)."""
    INTERNAL_ERROR = "internal_error"
    """The server logged an internal error while creating the configuration (500)."""


class TermConflictCode:
    """Machine-readable ``error_code`` of 409 refusals caused by the rental term.

    Read them through :attr:`intelion_cloud.exceptions.APIError.error_code`.
    Values mirror the constants in ``user_panel.services.term_obligation`` on
    the server. The body is ``{"error_code", "message", "detail"}``; the
    Russian ``message`` changes with copywriting, branch on the code. The
    server has other term codes too (``TERM_CONDITIONS_REQUIRED``,
    ``TERM_TERMINATION_REQUIRED`` and more): compare ``error_code`` with a
    string when you need one that is not listed here.
    """

    AUTO_RENEWAL_CONSENT_REQUIRED = "AUTO_RENEWAL_CONSENT_REQUIRED"
    """``update(is_auto_renewal=True)`` under a running confirmed term
    (``CloudServer.is_renewal_mandatory``). Turning auto-renewal on extends the
    term: only the customer can do it, with the switch on the server card in the
    web panel, never via API v2 (no consent window since 2026-09-29)."""
    AUTO_RENEWAL_NOT_APPLICABLE = "AUTO_RENEWAL_NOT_APPLICABLE"
    """``update(is_auto_renewal=True)`` while the toggle is fixed by a document:
    conditions accepted but the server not started yet
    (``term_state == "pending_consent"``), or a confirmed term that already
    ended and was neither stopped nor renewed."""
    TERM_RENEWAL_IN_PROGRESS = "TERM_RENEWAL_IN_PROGRESS"
    """``start()`` hit the short window while the term is being renewed:
    retry the start in about a minute."""
