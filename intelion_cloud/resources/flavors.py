"""Flavor resource — list available server configurations."""

from __future__ import annotations

from typing import List, Optional, Union

from .._pagination import PaginatedResponse
from ..models.flavors import Flavor
from ._base import AsyncResource, SyncResource

_PATH = "flavors/"


class Flavors(SyncResource):
    """Synchronous flavor operations."""

    def list(
        self,
        *,
        page: Optional[int] = None,
    ) -> Union[List[Flavor], PaginatedResponse[Flavor]]:
        """List available flavors.

        Without ``page``, returns all flavors (auto-paginated).
        With ``page=N``, returns a single :class:`PaginatedResponse`.
        """
        if page is not None:
            return self._list_page(_PATH, Flavor.from_dict, page=page)
        return self._list_all(_PATH, Flavor.from_dict)


class AsyncFlavors(AsyncResource):
    """Asynchronous flavor operations."""

    async def list(
        self,
        *,
        page: Optional[int] = None,
    ) -> Union[List[Flavor], PaginatedResponse[Flavor]]:
        if page is not None:
            return await self._list_page(_PATH, Flavor.from_dict, page=page)
        return await self._list_all(_PATH, Flavor.from_dict)
