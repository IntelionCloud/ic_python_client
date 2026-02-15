"""Flavor model — OpenStack server configuration template."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ._base import _get, _parse_nested
from .components import CPU, GPU, RAM


@dataclass(frozen=True)
class Flavor:
    """An OpenStack flavor describing a server hardware configuration template."""

    id: str  # UUID
    name: str
    cpu_count: int
    ram_count: float
    gpu_count: Optional[int]
    flavor_monthly_price_rub_cents: int
    flavor_hourly_price_rub_cents: int
    max_available: int
    cpu: Optional[CPU] = None
    ram: Optional[RAM] = None
    gpu: Optional[GPU] = None
    gpu_name: Optional[str] = None
    extra_specs: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Flavor:
        return cls(
            id=str(data["id"]),
            name=data.get("name", ""),
            cpu_count=data.get("cpu_count", 0),
            ram_count=data.get("ram_count", 0),
            gpu_count=_get(data, "gpu_count"),
            flavor_monthly_price_rub_cents=data.get("flavor_monthly_price_rub_cents", 0),
            flavor_hourly_price_rub_cents=data.get("flavor_hourly_price_rub_cents", 0),
            max_available=data.get("max_available", 0),
            cpu=_parse_nested(data, "cpu", CPU),
            ram=_parse_nested(data, "ram", RAM),
            gpu=_parse_nested(data, "gpu", GPU),
            gpu_name=_get(data, "gpu_name"),
            extra_specs=data.get("extra_specs") or {},
        )
