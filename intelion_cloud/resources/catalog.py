"""Hardware catalog resources — GPUs, CPUs, RAM, SSDs and software addons.

Read-only reference data: the same lists the configurator is built from.
These endpoints are public (no ``Authorization`` needed), but the SDK sends
the token anyway — harmless and keeps one client for everything.

⚠️ ``software-addons/`` paginates by ``limit``/``offset`` while the hardware
catalog paginates by ``page``. That is why :class:`SoftwareAddons` exposes no
``page`` argument: passing ``?page=N`` to a limit/offset endpoint is silently
ignored by DRF and you would get page 1 back believing it was page N. Use
``list()`` (auto-paginating) instead.
"""

from __future__ import annotations

from typing import List, Optional, Union

from .._pagination import PaginatedResponse
from ..models.components import CPU, GPU, RAM, SSD, SoftwareAddon
from ._base import AsyncResource, SyncResource

_GPU_PATH = "gpus/"
_CPU_PATH = "cpus/"
_RAM_PATH = "ram/"
_SSD_PATH = "ssds/"
_ADDON_PATH = "software-addons/"


class GPUs(SyncResource):
    """Synchronous GPU catalog."""

    def list(
        self, *, page: Optional[int] = None
    ) -> Union[List[GPU], PaginatedResponse[GPU]]:
        """List GPU models. Without ``page`` — all of them (auto-paginated)."""
        if page is not None:
            return self._list_page(_GPU_PATH, GPU.from_dict, page=page)
        return self._list_all(_GPU_PATH, GPU.from_dict)

    def get(self, gpu_id: int) -> GPU:
        return GPU.from_dict(self._get(f"{_GPU_PATH}{gpu_id}/"))


class CPUs(SyncResource):
    """Synchronous CPU catalog."""

    def list(
        self, *, page: Optional[int] = None
    ) -> Union[List[CPU], PaginatedResponse[CPU]]:
        if page is not None:
            return self._list_page(_CPU_PATH, CPU.from_dict, page=page)
        return self._list_all(_CPU_PATH, CPU.from_dict)

    def get(self, cpu_id: int) -> CPU:
        return CPU.from_dict(self._get(f"{_CPU_PATH}{cpu_id}/"))


class RAMs(SyncResource):
    """Synchronous RAM catalog."""

    def list(
        self, *, page: Optional[int] = None
    ) -> Union[List[RAM], PaginatedResponse[RAM]]:
        if page is not None:
            return self._list_page(_RAM_PATH, RAM.from_dict, page=page)
        return self._list_all(_RAM_PATH, RAM.from_dict)

    def get(self, ram_id: int) -> RAM:
        return RAM.from_dict(self._get(f"{_RAM_PATH}{ram_id}/"))


class SSDs(SyncResource):
    """Synchronous SSD catalog."""

    def list(
        self, *, page: Optional[int] = None
    ) -> Union[List[SSD], PaginatedResponse[SSD]]:
        if page is not None:
            return self._list_page(_SSD_PATH, SSD.from_dict, page=page)
        return self._list_all(_SSD_PATH, SSD.from_dict)

    def get(self, ssd_id: int) -> SSD:
        return SSD.from_dict(self._get(f"{_SSD_PATH}{ssd_id}/"))


class SoftwareAddons(SyncResource):
    """Synchronous software addon catalog (limit/offset pagination — no ``page``)."""

    def list(self) -> List[SoftwareAddon]:
        """List all active addons (auto-paginated over limit/offset)."""
        return self._list_all(_ADDON_PATH, SoftwareAddon.from_dict)

    def get(self, addon_id: int) -> SoftwareAddon:
        return SoftwareAddon.from_dict(self._get(f"{_ADDON_PATH}{addon_id}/"))


class AsyncGPUs(AsyncResource):
    """Asynchronous GPU catalog."""

    async def list(
        self, *, page: Optional[int] = None
    ) -> Union[List[GPU], PaginatedResponse[GPU]]:
        if page is not None:
            return await self._list_page(_GPU_PATH, GPU.from_dict, page=page)
        return await self._list_all(_GPU_PATH, GPU.from_dict)

    async def get(self, gpu_id: int) -> GPU:
        return GPU.from_dict(await self._get(f"{_GPU_PATH}{gpu_id}/"))


class AsyncCPUs(AsyncResource):
    """Asynchronous CPU catalog."""

    async def list(
        self, *, page: Optional[int] = None
    ) -> Union[List[CPU], PaginatedResponse[CPU]]:
        if page is not None:
            return await self._list_page(_CPU_PATH, CPU.from_dict, page=page)
        return await self._list_all(_CPU_PATH, CPU.from_dict)

    async def get(self, cpu_id: int) -> CPU:
        return CPU.from_dict(await self._get(f"{_CPU_PATH}{cpu_id}/"))


class AsyncRAMs(AsyncResource):
    """Asynchronous RAM catalog."""

    async def list(
        self, *, page: Optional[int] = None
    ) -> Union[List[RAM], PaginatedResponse[RAM]]:
        if page is not None:
            return await self._list_page(_RAM_PATH, RAM.from_dict, page=page)
        return await self._list_all(_RAM_PATH, RAM.from_dict)

    async def get(self, ram_id: int) -> RAM:
        return RAM.from_dict(await self._get(f"{_RAM_PATH}{ram_id}/"))


class AsyncSSDs(AsyncResource):
    """Asynchronous SSD catalog."""

    async def list(
        self, *, page: Optional[int] = None
    ) -> Union[List[SSD], PaginatedResponse[SSD]]:
        if page is not None:
            return await self._list_page(_SSD_PATH, SSD.from_dict, page=page)
        return await self._list_all(_SSD_PATH, SSD.from_dict)

    async def get(self, ssd_id: int) -> SSD:
        return SSD.from_dict(await self._get(f"{_SSD_PATH}{ssd_id}/"))


class AsyncSoftwareAddons(AsyncResource):
    """Asynchronous software addon catalog."""

    async def list(self) -> List[SoftwareAddon]:
        return await self._list_all(_ADDON_PATH, SoftwareAddon.from_dict)

    async def get(self, addon_id: int) -> SoftwareAddon:
        return SoftwareAddon.from_dict(await self._get(f"{_ADDON_PATH}{addon_id}/"))
