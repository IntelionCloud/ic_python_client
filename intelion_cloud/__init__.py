"""Intelion Cloud Python client.

Usage::

    from intelion_cloud import IntelionCloud

    client = IntelionCloud(token="your_api_token")
    servers = client.cloud_servers.list()
"""

from ._client import AsyncIntelionCloud, IntelionCloud
from .constants import BillingPeriod, PricePlan, ServerState
from .constants import ServerStatus as ServerStatusEnum
from .exceptions import (
    APIError,
    AuthenticationError,
    ConflictError,
    ConnectionError,
    ForbiddenError,
    IntelionCloudError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from .models import (
    CPU,
    GPU,
    OSImage,
    RAM,
    SSD,
    CloudServer,
    DebtInfo,
    Flavor,
    PhysicalServer,
    Promocode,
    ServerStatus,
    UsageAct,
    User,
    WhiteIP,
)

__version__ = "0.1.0"

__all__ = [
    # Clients
    "IntelionCloud",
    "AsyncIntelionCloud",
    # Models
    "CloudServer",
    "ServerStatus",
    "Flavor",
    "User",
    "GPU",
    "CPU",
    "RAM",
    "SSD",
    "OSImage",
    "UsageAct",
    "DebtInfo",
    "Promocode",
    "WhiteIP",
    "PhysicalServer",
    # Constants
    "ServerStatusEnum",
    "ServerState",
    "PricePlan",
    "BillingPeriod",
    # Exceptions
    "IntelionCloudError",
    "APIError",
    "AuthenticationError",
    "ForbiddenError",
    "NotFoundError",
    "ConflictError",
    "RateLimitError",
    "ValidationError",
    "ServerError",
    "ConnectionError",
]
