"""Cloud server and related billing models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ._base import _get, _parse_nested, _parse_nested_list
from .components import CPU, GPU, OSImage, RAM, SSD


@dataclass(frozen=True)
class DebtInfo:
    """Next payment / debt information for a usage act."""

    period_price_rub_cents: int
    periods_to_pay: int
    amount_rub_cents: int
    period_end_dt: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DebtInfo:
        return cls(
            period_price_rub_cents=data.get("period_price_rub_cents", 0),
            periods_to_pay=data.get("periods_to_pay", 0),
            amount_rub_cents=data.get("amount_rub_cents", 0),
            period_end_dt=_get(data, "period_end_dt"),
        )


@dataclass(frozen=True)
class UsageAct:
    """A billing period record (snapshot of prices at the time of creation)."""

    id: int
    user_config_id: int
    start_dt: Optional[str] = None
    stop_dt: Optional[str] = None
    monthly_price_rub: Optional[float] = None
    daily_price_rub: Optional[float] = None
    hourly_price_rub: Optional[float] = None
    period: Optional[int] = None
    periods_planned: Optional[int] = None
    cloud_server_uptime_seconds: int = 0
    cloud_srv_price_rub_cents: int = 0
    actual_cost_rub_cents: int = 0
    spent_amount_rub_cents: int = 0
    refund_amount_rub_cents: int = 0
    next_payment: Optional[DebtInfo] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UsageAct:
        return cls(
            id=data["id"],
            user_config_id=data.get("user_config_id", 0),
            start_dt=_get(data, "start_dt"),
            stop_dt=_get(data, "stop_dt"),
            monthly_price_rub=_get(data, "monthly_price_rub"),
            daily_price_rub=_get(data, "daily_price_rub"),
            hourly_price_rub=_get(data, "hourly_price_rub"),
            period=_get(data, "period"),
            periods_planned=_get(data, "periods_planned"),
            cloud_server_uptime_seconds=data.get("cloud_server_uptime_seconds", 0),
            cloud_srv_price_rub_cents=data.get("cloud_srv_price_rub_cents", 0),
            actual_cost_rub_cents=data.get("actual_cost_rub_cents", 0),
            spent_amount_rub_cents=data.get("spent_amount_rub_cents", 0),
            refund_amount_rub_cents=data.get("refund_amount_rub_cents", 0),
            next_payment=_parse_nested(data, "next_payment", DebtInfo),
        )


@dataclass(frozen=True)
class Promocode:
    """Applied promotional code."""

    id: int
    code: str
    discount_value: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Promocode:
        return cls(
            id=data["id"],
            code=data.get("code", ""),
            discount_value=data.get("discount_value", 0),
        )


@dataclass(frozen=True)
class WhiteIP:
    """A public IP address assigned to a server."""

    address_v4: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WhiteIP:
        return cls(address_v4=data.get("address_v4", ""))


@dataclass(frozen=True)
class PhysicalServer:
    """Physical server reference (for dedicated servers only)."""

    name: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PhysicalServer:
        return cls(name=data.get("name", ""))


@dataclass(frozen=True)
class SoftwareAddonInstance:
    """Software addon installed (or being installed) on a cloud server."""

    uca_id: int
    id: int
    name: str
    status: str
    port: Optional[int] = None
    access_token: str = ""
    progress_message: str = ""
    error_message: str = ""
    hardware_mode: str = ""
    last_heartbeat_dt: Optional[str] = None
    has_error: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SoftwareAddonInstance:
        return cls(
            uca_id=data["uca_id"],
            id=data["id"],
            name=data.get("name", ""),
            status=data.get("status", ""),
            port=_get(data, "port"),
            access_token=data.get("access_token", "") or "",
            progress_message=data.get("progress_message", "") or "",
            error_message=data.get("error_message", "") or "",
            hardware_mode=data.get("hardware_mode", "") or "",
            last_heartbeat_dt=_get(data, "last_heartbeat_dt"),
            has_error=data.get("has_error", False),
        )


@dataclass(frozen=True)
class CloudServer:
    """A cloud (or dedicated) server configuration.

    This is the main model returned by the cloud-servers API endpoints.
    Cloud servers have ``flavor_oid`` set; dedicated servers have it as ``None``.
    """

    id: int
    name: str
    status: int
    price_plan: int
    is_auto_renewal: bool
    monthly_price_rub_cents: int
    hourly_price_rub_cents: int
    server_full_rent_price_rub_cents: int
    flavor_oid: Optional[str] = None
    server_state: int = 0
    has_instance: bool = False
    credentials: str = ""
    ip_to_connect: Optional[str] = None
    domain_to_connect: Optional[str] = None
    login: str = ""
    gpu: Optional[GPU] = None
    gpu_count: int = 0
    cpu: Optional[CPU] = None
    cpu_count: int = 0
    ram: Optional[RAM] = None
    ram_count: int = 0
    network_disk: Optional[SSD] = None
    network_disk_count: int = 0
    local_disk: Optional[SSD] = None
    local_disk_count: int = 0
    os: Optional[OSImage] = None
    usage_act: Optional[UsageAct] = None
    last_finished_usage_act: Optional[UsageAct] = None
    last_usage_act: Optional[UsageAct] = None
    promocode: Optional[Promocode] = None
    physical_server: Optional[PhysicalServer] = None
    white_ips: List[WhiteIP] = field(default_factory=list)
    software_addons: List[SoftwareAddonInstance] = field(default_factory=list)
    card_background: Optional[str] = None
    monthly_price_rub: Optional[float] = None
    total_ram_size: int = 0
    total_network_disk_size: int = 0
    total_local_disk_size: int = 0
    max_available: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CloudServer:
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            status=data.get("status", 0),
            price_plan=data.get("price_plan", 0),
            is_auto_renewal=data.get("is_auto_renewal", False),
            monthly_price_rub_cents=data.get("monthly_price_rub_cents", 0),
            hourly_price_rub_cents=data.get("hourly_price_rub_cents", 0),
            server_full_rent_price_rub_cents=data.get("server_full_rent_price_rub_cents", 0),
            flavor_oid=_get(data, "flavor_oid"),
            server_state=data.get("server_state", 0),
            has_instance=data.get("has_instance", False),
            credentials=data.get("credentials", ""),
            ip_to_connect=_get(data, "ip_to_connect"),
            domain_to_connect=_get(data, "domain_to_connect"),
            login=data.get("login", ""),
            gpu=_parse_nested(data, "gpu", GPU),
            gpu_count=data.get("gpu_count", 0),
            cpu=_parse_nested(data, "cpu", CPU),
            cpu_count=data.get("cpu_count", 0),
            ram=_parse_nested(data, "ram", RAM),
            ram_count=data.get("ram_count", 0),
            network_disk=_parse_nested(data, "network_disk", SSD),
            network_disk_count=data.get("network_disk_count", 0),
            local_disk=_parse_nested(data, "local_disk", SSD),
            local_disk_count=data.get("local_disk_count", 0),
            os=_parse_nested(data, "os", OSImage),
            usage_act=_parse_nested(data, "usage_act", UsageAct),
            last_finished_usage_act=_parse_nested(data, "last_finished_usage_act", UsageAct),
            last_usage_act=_parse_nested(data, "last_usage_act", UsageAct),
            promocode=_parse_nested(data, "promocode", Promocode),
            physical_server=_parse_nested(data, "physical_server", PhysicalServer),
            white_ips=_parse_nested_list(data, "white_ips", WhiteIP),
            software_addons=_parse_nested_list(data, "software_addons", SoftwareAddonInstance),
            card_background=_get(data, "card_background"),
            monthly_price_rub=_get(data, "monthly_price_rub"),
            total_ram_size=data.get("total_ram_size", 0),
            total_network_disk_size=data.get("total_network_disk_size", 0),
            total_local_disk_size=data.get("total_local_disk_size", 0),
            max_available=data.get("max_available", 0),
        )


@dataclass(frozen=True)
class ServerStatus:
    """Result of the pre-start status check endpoint."""

    can_start: bool
    affordable_runtime_seconds: Optional[int] = None
    message: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ServerStatus:
        return cls(
            can_start=data.get("can_start", False),
            affordable_runtime_seconds=_get(data, "affordable_runtime_seconds"),
            message=_get(data, "message"),
        )
