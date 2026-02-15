"""Base utilities for model deserialization."""

from __future__ import annotations

from typing import Any, Dict, Optional, Type, TypeVar

T = TypeVar("T")


def _get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Get a value from dict, treating empty string as None."""
    val = data.get(key, default)
    if val == "":
        return default
    return val


def _parse_nested(
    data: Dict[str, Any],
    key: str,
    cls: Type[T],
) -> Optional[T]:
    """Parse a nested object from a dict if present and non-null."""
    val = data.get(key)
    if val is None or not isinstance(val, dict):
        return None
    return cls.from_dict(val)  # type: ignore[attr-defined]


def _parse_nested_list(
    data: Dict[str, Any],
    key: str,
    cls: Type[T],
) -> list:
    """Parse a list of nested objects."""
    val = data.get(key)
    if val is None or not isinstance(val, list):
        return []
    return [cls.from_dict(item) for item in val if isinstance(item, dict)]  # type: ignore[attr-defined]
