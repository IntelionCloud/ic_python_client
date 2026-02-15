"""Cloud server resource — CRUD, lifecycle actions, clone, migrate."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from .._pagination import PaginatedResponse
from ..models.servers import CloudServer, ServerStatus
from ._base import AsyncResource, SyncResource

_PATH = "cloud-servers/"
# server-orders/ is the creation endpoint (separate from cloud-servers/)
_CREATE_PATH = "server-orders/"


def _build_action_payload(
    status: Union[int, str],
    *,
    is_auto_renewal: Optional[bool] = None,
    run_on_affordable_time: bool = False,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"status": status}
    if is_auto_renewal is not None:
        payload["isAutoRenewal"] = is_auto_renewal
    if run_on_affordable_time:
        payload["run_on_affordable_time"] = True
    return payload


class CloudServers(SyncResource):
    """Synchronous cloud server operations."""

    def list(
        self,
        *,
        page: Optional[int] = None,
    ) -> Union[List[CloudServer], PaginatedResponse[CloudServer]]:
        """List cloud servers.

        Without ``page``, returns all servers (auto-paginated).
        With ``page=N``, returns a single :class:`PaginatedResponse`.
        """
        if page is not None:
            return self._list_page(_PATH, CloudServer.from_dict, page=page)
        return self._list_all(_PATH, CloudServer.from_dict)

    def get(self, server_id: int) -> CloudServer:
        """Get a single cloud server by ID."""
        data = self._get(f"{_PATH}{server_id}/")
        return CloudServer.from_dict(data)

    def create(
        self,
        *,
        name: str,
        flavor_id: str,
        cpu_id: int,
        cpu_count: int,
        ram_id: int,
        ram_count: int,
        ssd_count: int,
        os_id: int,
        price_plan: int = 0,
        gpu_id: Optional[int] = None,
        gpu_count: Optional[int] = None,
        promocode_id: Optional[int] = None,
        is_in_queue: bool = False,
    ) -> CloudServer:
        """Create a new cloud server configuration.

        Args:
            name: Server display name.
            flavor_id: OpenStack flavor UUID.
            cpu_id: CPU component ID.
            cpu_count: Number of CPUs.
            ram_id: RAM component ID.
            ram_count: Number of RAM modules.
            ssd_count: Number of NVMe drives.
            os_id: Operating system image ID.
            price_plan: Billing plan (use :class:`~intelion_cloud.constants.PricePlan`).
            gpu_id: GPU component ID (optional for CPU-only flavors).
            gpu_count: Number of GPUs.
            promocode_id: Promotional code ID to apply.
            is_in_queue: If True, queue the order when hardware is unavailable.
        """
        payload: Dict[str, Any] = {
            "name": name,
            "flavor_id": flavor_id,
            "cpu_id": cpu_id,
            "cpu_count": cpu_count,
            "ram_id": ram_id,
            "ram_count": ram_count,
            "ssd_count": ssd_count,
            "os_id": os_id,
            "price_plan": price_plan,
        }
        if gpu_id is not None:
            payload["gpu_id"] = gpu_id
        if gpu_count is not None:
            payload["gpu_count"] = gpu_count
        if promocode_id is not None:
            payload["promocode_id"] = promocode_id
        if is_in_queue:
            payload["is_in_queue"] = True

        data = self._post(_CREATE_PATH, json=payload)
        return CloudServer.from_dict(data)

    def update(
        self,
        server_id: int,
        *,
        name: Optional[str] = None,
        is_auto_renewal: Optional[bool] = None,
    ) -> CloudServer:
        """Update server properties (name, auto-renewal)."""
        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if is_auto_renewal is not None:
            payload["is_auto_renewal"] = is_auto_renewal
        data = self._patch(f"{_PATH}{server_id}/", json=payload)
        return CloudServer.from_dict(data)

    # --- Lifecycle actions ---

    def start(
        self,
        server_id: int,
        *,
        is_auto_renewal: Optional[bool] = None,
        run_on_affordable_time: bool = False,
    ) -> CloudServer:
        """Start a stopped server."""
        payload = _build_action_payload(
            2,  # ServerStatus.ACTIVE
            is_auto_renewal=is_auto_renewal,
            run_on_affordable_time=run_on_affordable_time,
        )
        data = self._post(f"{_PATH}{server_id}/actions/", json=payload)
        return CloudServer.from_dict(data)

    def stop(self, server_id: int) -> CloudServer:
        """Stop (shelve) a running server."""
        data = self._post(f"{_PATH}{server_id}/actions/", json={"status": -1})
        return CloudServer.from_dict(data)

    def reboot(self, server_id: int) -> CloudServer:
        """Reboot a running server."""
        data = self._post(f"{_PATH}{server_id}/actions/", json={"status": "REBOOT"})
        return CloudServer.from_dict(data)

    def delete(self, server_id: int) -> CloudServer:
        """Delete a server (irreversible)."""
        data = self._post(f"{_PATH}{server_id}/actions/", json={"status": -3})
        return CloudServer.from_dict(data)

    # --- Info endpoints ---

    def get_status(self, server_id: int) -> ServerStatus:
        """Check if a server can be started and get affordable runtime."""
        data = self._get(f"{_PATH}{server_id}/status/")
        return ServerStatus.from_dict(data)

    def get_password(self, server_id: int) -> str:
        """Get the server password (available after first boot)."""
        data = self._get(f"{_PATH}{server_id}/password/")
        if isinstance(data, dict):
            return data.get("password", "")
        return str(data)

    # --- Advanced operations ---

    def clone(self, server_id: int) -> CloudServer:
        """Clone a server (creates an identical copy)."""
        data = self._post(f"{_PATH}{server_id}/clone/")
        return CloudServer.from_dict(data)

    def migrate(
        self,
        server_id: int,
        *,
        flavor_id: str,
        price_plan: int,
        gpu_id: Optional[int] = None,
        gpu_count: Optional[int] = None,
        cpu_id: Optional[int] = None,
        cpu_count: Optional[int] = None,
        ram_id: Optional[int] = None,
        ram_count: Optional[int] = None,
    ) -> CloudServer:
        """Migrate a server to a different configuration.

        The server must be stopped before migration.
        """
        payload: Dict[str, Any] = {
            "flavor_id": flavor_id,
            "price_plan": price_plan,
        }
        if gpu_id is not None:
            payload["gpu_id"] = gpu_id
        if gpu_count is not None:
            payload["gpu_count"] = gpu_count
        if cpu_id is not None:
            payload["cpu_id"] = cpu_id
        if cpu_count is not None:
            payload["cpu_count"] = cpu_count
        if ram_id is not None:
            payload["ram_id"] = ram_id
        if ram_count is not None:
            payload["ram_count"] = ram_count

        data = self._post(f"{_PATH}{server_id}/migrate/", json=payload)
        return CloudServer.from_dict(data)


class AsyncCloudServers(AsyncResource):
    """Asynchronous cloud server operations."""

    async def list(
        self,
        *,
        page: Optional[int] = None,
    ) -> Union[List[CloudServer], PaginatedResponse[CloudServer]]:
        if page is not None:
            return await self._list_page(_PATH, CloudServer.from_dict, page=page)
        return await self._list_all(_PATH, CloudServer.from_dict)

    async def get(self, server_id: int) -> CloudServer:
        data = await self._get(f"{_PATH}{server_id}/")
        return CloudServer.from_dict(data)

    async def create(
        self,
        *,
        name: str,
        flavor_id: str,
        cpu_id: int,
        cpu_count: int,
        ram_id: int,
        ram_count: int,
        ssd_count: int,
        os_id: int,
        price_plan: int = 0,
        gpu_id: Optional[int] = None,
        gpu_count: Optional[int] = None,
        promocode_id: Optional[int] = None,
        is_in_queue: bool = False,
    ) -> CloudServer:
        payload: Dict[str, Any] = {
            "name": name,
            "flavor_id": flavor_id,
            "cpu_id": cpu_id,
            "cpu_count": cpu_count,
            "ram_id": ram_id,
            "ram_count": ram_count,
            "ssd_count": ssd_count,
            "os_id": os_id,
            "price_plan": price_plan,
        }
        if gpu_id is not None:
            payload["gpu_id"] = gpu_id
        if gpu_count is not None:
            payload["gpu_count"] = gpu_count
        if promocode_id is not None:
            payload["promocode_id"] = promocode_id
        if is_in_queue:
            payload["is_in_queue"] = True

        data = await self._post(_CREATE_PATH, json=payload)
        return CloudServer.from_dict(data)

    async def update(
        self,
        server_id: int,
        *,
        name: Optional[str] = None,
        is_auto_renewal: Optional[bool] = None,
    ) -> CloudServer:
        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if is_auto_renewal is not None:
            payload["is_auto_renewal"] = is_auto_renewal
        data = await self._patch(f"{_PATH}{server_id}/", json=payload)
        return CloudServer.from_dict(data)

    async def start(
        self,
        server_id: int,
        *,
        is_auto_renewal: Optional[bool] = None,
        run_on_affordable_time: bool = False,
    ) -> CloudServer:
        payload = _build_action_payload(
            2,
            is_auto_renewal=is_auto_renewal,
            run_on_affordable_time=run_on_affordable_time,
        )
        data = await self._post(f"{_PATH}{server_id}/actions/", json=payload)
        return CloudServer.from_dict(data)

    async def stop(self, server_id: int) -> CloudServer:
        data = await self._post(f"{_PATH}{server_id}/actions/", json={"status": -1})
        return CloudServer.from_dict(data)

    async def reboot(self, server_id: int) -> CloudServer:
        data = await self._post(f"{_PATH}{server_id}/actions/", json={"status": "REBOOT"})
        return CloudServer.from_dict(data)

    async def delete(self, server_id: int) -> CloudServer:
        data = await self._post(f"{_PATH}{server_id}/actions/", json={"status": -3})
        return CloudServer.from_dict(data)

    async def get_status(self, server_id: int) -> ServerStatus:
        data = await self._get(f"{_PATH}{server_id}/status/")
        return ServerStatus.from_dict(data)

    async def get_password(self, server_id: int) -> str:
        data = await self._get(f"{_PATH}{server_id}/password/")
        if isinstance(data, dict):
            return data.get("password", "")
        return str(data)

    async def clone(self, server_id: int) -> CloudServer:
        data = await self._post(f"{_PATH}{server_id}/clone/")
        return CloudServer.from_dict(data)

    async def migrate(
        self,
        server_id: int,
        *,
        flavor_id: str,
        price_plan: int,
        gpu_id: Optional[int] = None,
        gpu_count: Optional[int] = None,
        cpu_id: Optional[int] = None,
        cpu_count: Optional[int] = None,
        ram_id: Optional[int] = None,
        ram_count: Optional[int] = None,
    ) -> CloudServer:
        payload: Dict[str, Any] = {
            "flavor_id": flavor_id,
            "price_plan": price_plan,
        }
        if gpu_id is not None:
            payload["gpu_id"] = gpu_id
        if gpu_count is not None:
            payload["gpu_count"] = gpu_count
        if cpu_id is not None:
            payload["cpu_id"] = cpu_id
        if cpu_count is not None:
            payload["cpu_count"] = cpu_count
        if ram_id is not None:
            payload["ram_id"] = ram_id
        if ram_count is not None:
            payload["ram_count"] = ram_count

        data = await self._post(f"{_PATH}{server_id}/migrate/", json=payload)
        return CloudServer.from_dict(data)
