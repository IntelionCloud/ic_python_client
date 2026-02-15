"""Pagination helpers for DRF paginated responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar
from urllib.parse import parse_qs, urlparse

T = TypeVar("T")


@dataclass
class PaginatedResponse(Generic[T]):
    """A single page of results from the API."""

    count: int
    results: List[T]
    next_url: Optional[str] = None
    previous_url: Optional[str] = None

    @property
    def has_next(self) -> bool:
        return self.next_url is not None


def parse_paginated(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract pagination metadata from a DRF response.

    Returns dict with 'count', 'next', 'previous', 'results'.
    If the response is not paginated (plain list), wraps it.
    """
    if isinstance(data, list):
        return {"count": len(data), "next": None, "previous": None, "results": data}
    return {
        "count": data.get("count", 0),
        "next": data.get("next"),
        "previous": data.get("previous"),
        "results": data.get("results", []),
    }


def extract_next_page(url: Optional[str]) -> Optional[Tuple[str, Dict[str, str]]]:
    """Convert an absolute next/previous URL to (path, params) for the transport.

    Returns None if URL is None, otherwise (relative_path, query_params).

    Example:
        'https://intelion.cloud/api/v2/flavors/?page=2'
        -> ('flavors/', {'page': '2'})
    """
    if url is None:
        return None

    parsed = urlparse(url)

    # Extract relative path after /api/v2/
    path = parsed.path
    marker = "/api/v2/"
    idx = path.find(marker)
    if idx >= 0:
        path = path[idx + len(marker) :]

    # Parse query string into flat dict (take first value of each key)
    params = {k: v[0] for k, v in parse_qs(parsed.query).items()}

    return path, params
