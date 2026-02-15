"""Enumerations and constants matching the Intelion Cloud API."""

from enum import IntEnum

__all__ = [
    "ServerStatus",
    "ServerState",
    "PricePlan",
    "BillingPeriod",
    "OSType",
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
