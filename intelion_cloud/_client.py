"""Main client classes: IntelionCloud (sync) and AsyncIntelionCloud (async)."""

from __future__ import annotations

from typing import Optional

from .constants import DEFAULT_BASE_URL, DEFAULT_CONNECT_TIMEOUT, DEFAULT_TIMEOUT
from ._transport import AsyncTransport, SyncTransport
from .resources.cloud_servers import AsyncCloudServers, CloudServers
from .resources.catalog import (
    AsyncCPUs,
    AsyncGPUs,
    AsyncRAMs,
    AsyncSoftwareAddons,
    AsyncSSDs,
    CPUs,
    GPUs,
    RAMs,
    SoftwareAddons,
    SSDs,
)
from .resources.flavors import AsyncFlavors, Flavors
from .resources.inference_api_keys import AsyncInferenceApiKeys, InferenceApiKeys
from .resources.os_images import AsyncOSImages, OSImages
from .resources.ssh_keys import AsyncSSHKeys, SSHKeys
from .resources.users import AsyncUsers, Users


class IntelionCloud:
    """Synchronous client for the Intelion Cloud API.

    Usage::

        client = IntelionCloud(token="your_api_token")
        servers = client.cloud_servers.list()
        client.close()

    Or as a context manager::

        with IntelionCloud(token="your_api_token") as client:
            servers = client.cloud_servers.list()

    Args:
        token: API authentication token (``Authorization: Token <token>``).
        base_url: Base URL of the Intelion Cloud instance.
        timeout: Overall request timeout in seconds.
        connect_timeout: Connection establishment timeout in seconds.
    """

    def __init__(
        self,
        token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
    ) -> None:
        self._transport = SyncTransport(
            token=token,
            base_url=base_url,
            timeout=timeout,
            connect_timeout=connect_timeout,
        )
        self.cloud_servers = CloudServers(self._transport)
        self.flavors = Flavors(self._transport)
        self.os_images = OSImages(self._transport)
        self.users = Users(self._transport)
        self.ssh_keys = SSHKeys(self._transport)
        self.gpus = GPUs(self._transport)
        self.cpus = CPUs(self._transport)
        self.ram = RAMs(self._transport)
        self.ssds = SSDs(self._transport)
        self.software_addons = SoftwareAddons(self._transport)
        self.inference_api_keys = InferenceApiKeys(self._transport)

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._transport.close()

    def __enter__(self) -> IntelionCloud:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class AsyncIntelionCloud:
    """Asynchronous client for the Intelion Cloud API.

    Usage::

        async with AsyncIntelionCloud(token="your_api_token") as client:
            servers = await client.cloud_servers.list()

    Args:
        token: API authentication token (``Authorization: Token <token>``).
        base_url: Base URL of the Intelion Cloud instance.
        timeout: Overall request timeout in seconds.
        connect_timeout: Connection establishment timeout in seconds.
    """

    def __init__(
        self,
        token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
    ) -> None:
        self._transport = AsyncTransport(
            token=token,
            base_url=base_url,
            timeout=timeout,
            connect_timeout=connect_timeout,
        )
        self.cloud_servers = AsyncCloudServers(self._transport)
        self.flavors = AsyncFlavors(self._transport)
        self.os_images = AsyncOSImages(self._transport)
        self.users = AsyncUsers(self._transport)
        self.ssh_keys = AsyncSSHKeys(self._transport)
        self.gpus = AsyncGPUs(self._transport)
        self.cpus = AsyncCPUs(self._transport)
        self.ram = AsyncRAMs(self._transport)
        self.ssds = AsyncSSDs(self._transport)
        self.software_addons = AsyncSoftwareAddons(self._transport)
        self.inference_api_keys = AsyncInferenceApiKeys(self._transport)

    async def close(self) -> None:
        """Close the underlying async HTTP connection pool."""
        await self._transport.close()

    async def __aenter__(self) -> AsyncIntelionCloud:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
