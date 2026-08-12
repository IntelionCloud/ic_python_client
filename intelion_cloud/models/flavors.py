"""Flavor model — server hardware configuration (FlavorConfig)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ._base import _get, _parse_nested
from .components import CPU, GPU, RAM


@dataclass(frozen=True)
class FlavorSubstitution:
    """A replacement flavor offered when the requested GPU is queue-disabled.

    The API returns this instead of letting you queue for a card that is
    fully leased out long-term — such a queue would never come up. Serialized
    by ``servers.services.flavors._serialize_substitution`` on the server side.
    """

    flavor_id: int
    flavor_name: str
    gpu_id: int
    gpu_slug: str
    gpu_name: str
    gpu_ram: int
    gpu_count: int
    cpu_id: int
    cpu_count: int
    ram_id: int
    ram_count: int
    monthly_price_rub_cents: int
    hourly_price_rub_cents: int
    exact_match: bool = True
    """``False`` — no exact cpu/ram equivalent exists on the replacement card,
    the closest one was picked. Surface this to the user rather than hiding it."""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FlavorSubstitution:
        return cls(
            flavor_id=data["flavor_id"],
            flavor_name=data.get("flavor_name", ""),
            gpu_id=data.get("gpu_id", 0),
            gpu_slug=data.get("gpu_slug", ""),
            gpu_name=data.get("gpu_name", ""),
            gpu_ram=data.get("gpu_ram", 0),
            gpu_count=data.get("gpu_count", 0),
            cpu_id=data.get("cpu_id", 0),
            cpu_count=data.get("cpu_count", 0),
            ram_id=data.get("ram_id", 0),
            ram_count=data.get("ram_count", 0),
            monthly_price_rub_cents=data.get("monthly_price_rub_cents", 0),
            hourly_price_rub_cents=data.get("hourly_price_rub_cents", 0),
            exact_match=data.get("exact_match", True),
        )


@dataclass(frozen=True)
class Flavor:
    """A flavor describing a server hardware configuration template (backed by FlavorConfig)."""

    id: int
    name: str
    cpu_count: int
    ram_count: int
    gpu_count: Optional[int]
    flavor_monthly_price_rub_cents: int
    flavor_hourly_price_rub_cents: int
    max_available: int
    openstack_id: Optional[str] = None
    cpu: Optional[CPU] = None
    ram: Optional[RAM] = None
    gpu: Optional[GPU] = None
    queue_disabled: bool = False
    """The GPU is leased out long-term: queueing for it is refused (HTTP 409)."""
    suggested_alternative: Optional[FlavorSubstitution] = None
    """Set only when ``queue_disabled`` and ``max_available == 0`` — otherwise ``None``."""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Flavor:
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            cpu_count=data.get("cpu_count", 0),
            ram_count=data.get("ram_count", 0),
            gpu_count=_get(data, "gpu_count"),
            flavor_monthly_price_rub_cents=data.get("flavor_monthly_price_rub_cents", 0),
            flavor_hourly_price_rub_cents=data.get("flavor_hourly_price_rub_cents", 0),
            max_available=data.get("max_available", 0),
            openstack_id=_get(data, "openstack_id"),
            cpu=_parse_nested(data, "cpu", CPU),
            ram=_parse_nested(data, "ram", RAM),
            gpu=_parse_nested(data, "gpu", GPU),
            queue_disabled=bool(data.get("queue_disabled", False)),
            suggested_alternative=_parse_nested(
                data, "suggested_alternative", FlavorSubstitution
            ),
        )
