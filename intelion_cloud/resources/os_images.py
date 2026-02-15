"""OS image resource — list available operating system images."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from .._pagination import PaginatedResponse
from ..models.components import OSImage
from ._base import AsyncResource, SyncResource

_PATH = "os-images/"


class OSImages(SyncResource):
    """Synchronous OS image operations."""

    def list(
        self,
        *,
        gpu_id: Optional[int] = None,
        page: Optional[int] = None,
    ) -> Union[List[OSImage], PaginatedResponse[OSImage]]:
        """List available OS images.

        Args:
            gpu_id: Filter images compatible with a specific GPU.
            page: If given, return a single page instead of all results.
        """
        params: Dict[str, Any] = {}
        if gpu_id is not None:
            params["gpu_id"] = gpu_id

        if page is not None:
            return self._list_page(_PATH, OSImage.from_dict, params=params or None, page=page)
        return self._list_all(_PATH, OSImage.from_dict, params=params or None)


class AsyncOSImages(AsyncResource):
    """Asynchronous OS image operations."""

    async def list(
        self,
        *,
        gpu_id: Optional[int] = None,
        page: Optional[int] = None,
    ) -> Union[List[OSImage], PaginatedResponse[OSImage]]:
        params: Dict[str, Any] = {}
        if gpu_id is not None:
            params["gpu_id"] = gpu_id

        if page is not None:
            return await self._list_page(
                _PATH, OSImage.from_dict, params=params or None, page=page
            )
        return await self._list_all(_PATH, OSImage.from_dict, params=params or None)
