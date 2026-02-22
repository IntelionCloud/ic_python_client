"""Hardware component models (GPU, CPU, RAM, SSD, OSImage)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ._base import _get


@dataclass(frozen=True)
class GPU:
    """Graphics processing unit specification."""

    id: int
    name: str
    slug: str
    group_title: str
    cuda_cores: int
    tensor_cores: int
    ram: int
    ram_type: str
    is_cloud: bool
    monthly_price_rub_cents: int
    hourly_price_rub_cents: int
    daily_price_rub_cents: int
    monthly_price_rub: Optional[float] = None
    hourly_price_rub: Optional[float] = None
    daily_price_rub: Optional[float] = None
    old_monthly_price_rub: Optional[float] = None
    discount_percent: int = 0
    tmu: Optional[int] = None
    rop: Optional[int] = None
    ram_capacity: Optional[int] = None
    processor: Optional[str] = None
    cover: Optional[str] = None
    description: Optional[str] = None
    l1_cache: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GPU:
        return cls(
            id=data["id"],
            name=data["name"],
            slug=data.get("slug", ""),
            group_title=data.get("group_title", ""),
            cuda_cores=data.get("cuda_cores", 0),
            tensor_cores=data.get("tensor_cores", 0),
            ram=data.get("ram", 0),
            ram_type=data.get("ram_type", ""),
            is_cloud=data.get("is_cloud", False),
            monthly_price_rub_cents=data.get("monthly_price_rub_cents", 0),
            hourly_price_rub_cents=data.get("hourly_price_rub_cents", 0),
            daily_price_rub_cents=data.get("daily_price_rub_cents", 0),
            monthly_price_rub=_get(data, "monthly_price_rub"),
            hourly_price_rub=_get(data, "hourly_price_rub"),
            daily_price_rub=_get(data, "daily_price_rub"),
            old_monthly_price_rub=_get(data, "old_monthly_price_rub"),
            discount_percent=data.get("discount_percent", 0),
            tmu=_get(data, "tmu"),
            rop=_get(data, "rop"),
            ram_capacity=_get(data, "ram_capacity"),
            processor=_get(data, "processor"),
            cover=_get(data, "cover"),
            description=_get(data, "description"),
            l1_cache=_get(data, "l1_cache"),
        )


@dataclass(frozen=True)
class CPU:
    """CPU specification."""

    id: int
    name: str
    cores: int
    threads: int
    monthly_price_rub_cents: int
    hourly_price_rub_cents: int
    daily_price_rub_cents: int
    group_title: str = ""
    freq_base: Optional[float] = None
    freq_turbo: Optional[float] = None
    l3_cache: Optional[float] = None
    ram_channels: Optional[int] = None
    ram_max_size: Optional[int] = None
    has_ecc_ram_support: bool = False
    cover: Optional[str] = None
    min_count: int = 1
    max_count: int = 1
    monthly_price_rub: Optional[float] = None
    hourly_price_rub: Optional[float] = None
    daily_price_rub: Optional[float] = None
    old_monthly_price_rub: Optional[float] = None
    discount_percent: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CPU:
        return cls(
            id=data["id"],
            name=data["name"],
            cores=data.get("cores", 0),
            threads=data.get("threads", 0),
            monthly_price_rub_cents=data.get("monthly_price_rub_cents", 0),
            hourly_price_rub_cents=data.get("hourly_price_rub_cents", 0),
            daily_price_rub_cents=data.get("daily_price_rub_cents", 0),
            group_title=data.get("group_title", ""),
            freq_base=_get(data, "freq_base"),
            freq_turbo=_get(data, "freq_turbo"),
            l3_cache=_get(data, "l3_cache"),
            ram_channels=_get(data, "ram_channels"),
            ram_max_size=_get(data, "ram_max_size"),
            has_ecc_ram_support=data.get("has_ecc_ram_support", False),
            cover=_get(data, "cover"),
            min_count=data.get("min_count", 1),
            max_count=data.get("max_count", 1),
            monthly_price_rub=_get(data, "monthly_price_rub"),
            hourly_price_rub=_get(data, "hourly_price_rub"),
            daily_price_rub=_get(data, "daily_price_rub"),
            old_monthly_price_rub=_get(data, "old_monthly_price_rub"),
            discount_percent=data.get("discount_percent", 0),
        )


@dataclass(frozen=True)
class RAM:
    """RAM module specification."""

    id: int
    size: int
    is_ecc: bool
    standard: int
    monthly_price_rub_cents: int
    hourly_price_rub_cents: int
    daily_price_rub_cents: int
    group_title: str = ""
    monthly_price_rub: Optional[float] = None
    hourly_price_rub: Optional[float] = None
    daily_price_rub: Optional[float] = None
    old_monthly_price_rub: Optional[float] = None
    discount_percent: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RAM:
        return cls(
            id=data["id"],
            size=data.get("size", 0),
            is_ecc=data.get("is_ecc", False),
            standard=data.get("standard", 4),
            monthly_price_rub_cents=data.get("monthly_price_rub_cents", 0),
            hourly_price_rub_cents=data.get("hourly_price_rub_cents", 0),
            daily_price_rub_cents=data.get("daily_price_rub_cents", 0),
            group_title=data.get("group_title", ""),
            monthly_price_rub=_get(data, "monthly_price_rub"),
            hourly_price_rub=_get(data, "hourly_price_rub"),
            daily_price_rub=_get(data, "daily_price_rub"),
            old_monthly_price_rub=_get(data, "old_monthly_price_rub"),
            discount_percent=data.get("discount_percent", 0),
        )


@dataclass(frozen=True)
class SSD:
    """SSD/NVMe drive specification."""

    id: int
    size: int
    group_title: str
    monthly_price_rub_cents: int
    hourly_price_rub_cents: int
    daily_price_rub_cents: int
    monthly_price_rub: Optional[float] = None
    hourly_price_rub: Optional[float] = None
    daily_price_rub: Optional[float] = None
    old_monthly_price_rub: Optional[float] = None
    discount_percent: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SSD:
        return cls(
            id=data["id"],
            size=data.get("size", 0),
            group_title=data.get("group_title", ""),
            monthly_price_rub_cents=data.get("monthly_price_rub_cents", 0),
            hourly_price_rub_cents=data.get("hourly_price_rub_cents", 0),
            daily_price_rub_cents=data.get("daily_price_rub_cents", 0),
            monthly_price_rub=_get(data, "monthly_price_rub"),
            hourly_price_rub=_get(data, "hourly_price_rub"),
            daily_price_rub=_get(data, "daily_price_rub"),
            old_monthly_price_rub=_get(data, "old_monthly_price_rub"),
            discount_percent=data.get("discount_percent", 0),
        )



@dataclass(frozen=True)
class OSImage:
    """Operating system image available for server deployment."""

    id: int
    name: str
    type: str
    description: str = ""
    ssh_enabled: bool = False
    rdp_enabled: bool = False
    compatible_gpu_ids: Optional[List[int]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> OSImage:
        return cls(
            id=data["id"],
            name=data["name"],
            type=data.get("type", ""),
            description=data.get("description", ""),
            ssh_enabled=data.get("ssh_enabled", False),
            rdp_enabled=data.get("rdp_enabled", False),
            compatible_gpu_ids=data.get("compatible_gpu_ids"),
        )
