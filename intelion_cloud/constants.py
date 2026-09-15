"""Enumerations and constants matching the Intelion Cloud API."""

from enum import IntEnum

__all__ = [
    "ServerStatus",
    "ServerState",
    "PricePlan",
    "BillingPeriod",
    "OSType",
    "TermState",
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
