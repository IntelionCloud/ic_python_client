"""Cloud server resource — CRUD, lifecycle actions, clone, migrate."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from .._pagination import PaginatedResponse
from ..models.servers import CloudServer, ServerStatus
from ._base import AsyncResource, SyncResource

_PATH = "cloud-servers/"


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
        flavor_id: int,
        ssd_count: int,
        os_id: int,
        price_plan: int = 0,
        promocode_id: Optional[int] = None,
        is_in_queue: bool = False,
        addon_ids: Optional[List[int]] = None,
    ) -> CloudServer:
        """Create a new cloud server configuration.

        Args:
            name: Server display name.
            flavor_id: FlavorConfig primary key. CPU/RAM/GPU are fixed by the flavor.
            ssd_count: Network disk size in GB (min 30). Maps to ``network_disk_count`` server-side.
            os_id: Operating system image ID (must be compatible with the flavor).
            price_plan: Billing plan (use :class:`~intelion_cloud.constants.PricePlan`).
            promocode_id: Promotional code ID to apply.
            is_in_queue: If True, queue the order when hardware is unavailable.
            addon_ids: Software addon IDs to install at first boot.
        """
        payload: Dict[str, Any] = {
            "name": name,
            "flavor_id": flavor_id,
            "ssd_count": ssd_count,
            "os_id": os_id,
            "price_plan": price_plan,
        }
        if promocode_id is not None:
            payload["promocode_id"] = promocode_id
        if is_in_queue:
            payload["is_in_queue"] = True
        if addon_ids:
            payload["addon_ids"] = list(addon_ids)

        data = self._post(_PATH, json=payload)
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

    def reinstall_os(self, server_id: int) -> CloudServer:
        """Reinstall the OS on a server, wiping the boot disk.

        All data on the boot disk is destroyed. The current monthly billing
        cycle is preserved (the open UsageAct is reused). A new IP and root
        password are generated and become available in the user panel a few
        minutes after the call returns.
        """
        data = self._post(f"{_PATH}{server_id}/reinstall-os/")
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
        flavor_id: int,
        price_plan: int,
    ) -> CloudServer:
        """Migrate a server to a different FlavorConfig and/or price plan.

        The server must be stopped before migration. CPU/RAM/GPU are fixed by the flavor.
        """
        payload: Dict[str, Any] = {
            "flavor_id": flavor_id,
            "price_plan": price_plan,
        }
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
        flavor_id: int,
        ssd_count: int,
        os_id: int,
        price_plan: int = 0,
        promocode_id: Optional[int] = None,
        is_in_queue: bool = False,
        addon_ids: Optional[List[int]] = None,
    ) -> CloudServer:
        payload: Dict[str, Any] = {
            "name": name,
            "flavor_id": flavor_id,
            "ssd_count": ssd_count,
            "os_id": os_id,
            "price_plan": price_plan,
        }
        if promocode_id is not None:
            payload["promocode_id"] = promocode_id
        if is_in_queue:
            payload["is_in_queue"] = True
        if addon_ids:
            payload["addon_ids"] = list(addon_ids)

        data = await self._post(_PATH, json=payload)
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

    async def reinstall_os(self, server_id: int) -> CloudServer:
        """Reinstall the OS on a server, wiping the boot disk."""
        data = await self._post(f"{_PATH}{server_id}/reinstall-os/")
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
        flavor_id: int,
        price_plan: int,
    ) -> CloudServer:
        payload: Dict[str, Any] = {
            "flavor_id": flavor_id,
            "price_plan": price_plan,
        }
        data = await self._post(f"{_PATH}{server_id}/migrate/", json=payload)
        return CloudServer.from_dict(data)
