"""Base resource classes providing HTTP methods to resource subclasses."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, TypeVar

from .._pagination import PaginatedResponse, extract_next_page, parse_paginated
from .._transport import AsyncTransport, SyncTransport

T = TypeVar("T")


class SyncResource:
    """Base class for synchronous API resources."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def _get(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> Any:
        response = self._transport.request("GET", path, params=params)
        return response.json()

    def _post(
        self,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        response = self._transport.request("POST", path, json=json, params=params)
        if response.status_code == 204:
            return None
        return response.json()

    def _patch(self, path: str, *, json: Dict[str, Any]) -> Any:
        response = self._transport.request("PATCH", path, json=json)
        return response.json()

    def _delete(self, path: str) -> None:
        """DELETE returning no body (204). Errors are raised by the transport."""
        self._transport.request("DELETE", path)

    def _list_all(
        self,
        path: str,
        model_cls: Callable[[Dict[str, Any]], T],
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[T]:
        """Fetch all pages and return a flat list of model instances."""
        all_items: List[T] = []
        current_path = path
        current_params = params

        while True:
            data = self._get(current_path, params=current_params)
            page = parse_paginated(data)
            all_items.extend(model_cls(item) for item in page["results"])

            next_info = extract_next_page(page["next"])
            if next_info is None:
                break
            current_path, current_params = next_info

        return all_items

    def _list_page(
        self,
        path: str,
        model_cls: Callable[[Dict[str, Any]], T],
        *,
        params: Optional[Dict[str, Any]] = None,
        page: int = 1,
    ) -> PaginatedResponse[T]:
        """Fetch a single page of results."""
        params = dict(params) if params else {}
        params["page"] = page
        data = self._get(path, params=params)
        paginated = parse_paginated(data)
        return PaginatedResponse(
            count=paginated["count"],
            results=[model_cls(item) for item in paginated["results"]],
            next_url=paginated["next"],
            previous_url=paginated["previous"],
        )


class AsyncResource:
    """Base class for asynchronous API resources."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def _get(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> Any:
        response = await self._transport.request("GET", path, params=params)
        return response.json()

    async def _post(
        self,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        response = await self._transport.request("POST", path, json=json, params=params)
        if response.status_code == 204:
            return None
        return response.json()

    async def _patch(self, path: str, *, json: Dict[str, Any]) -> Any:
        response = await self._transport.request("PATCH", path, json=json)
        return response.json()

    async def _delete(self, path: str) -> None:
        """DELETE returning no body (204). Errors are raised by the transport."""
        await self._transport.request("DELETE", path)

    async def _list_all(
        self,
        path: str,
        model_cls: Callable[[Dict[str, Any]], T],
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[T]:
        """Fetch all pages and return a flat list of model instances."""
        all_items: List[T] = []
        current_path = path
        current_params = params

        while True:
            data = await self._get(current_path, params=current_params)
            page = parse_paginated(data)
            all_items.extend(model_cls(item) for item in page["results"])

            next_info = extract_next_page(page["next"])
            if next_info is None:
                break
            current_path, current_params = next_info

        return all_items

    async def _list_page(
        self,
        path: str,
        model_cls: Callable[[Dict[str, Any]], T],
        *,
        params: Optional[Dict[str, Any]] = None,
        page: int = 1,
    ) -> PaginatedResponse[T]:
        """Fetch a single page of results."""
        params = dict(params) if params else {}
        params["page"] = page
        data = await self._get(path, params=params)
        paginated = parse_paginated(data)
        return PaginatedResponse(
            count=paginated["count"],
            results=[model_cls(item) for item in paginated["results"]],
            next_url=paginated["next"],
            previous_url=paginated["previous"],
        )
