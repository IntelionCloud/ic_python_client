"""Cloud server and related billing models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ._base import _get, _parse_nested, _parse_nested_list
from .components import CPU, GPU, OSImage, RAM, SSD
from .flavors import FlavorSubstitution


@dataclass(frozen=True)
class PasswordRotation:
    """Root password rotation notice for a server.

    Present only as an accomplished fact: a pending rotation is deliberately
    not exposed by the API. ``acknowledged`` is kept server-side so the notice
    is not shown again from a different client.
    """

    status: str
    """``"rotated"`` or ``"failed"``."""
    rotated_at: Optional[str] = None
    acknowledged: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PasswordRotation:
        return cls(
            status=data.get("status", ""),
            rotated_at=_get(data, "rotated_at"),
            acknowledged=data.get("acknowledged", False),
        )


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
    next_charge_rub_cents: int = 0
    """What the next charge will take from the balance (held-up money), kopecks."""
    full_period_cost_rub_cents: int = 0
    """Full cost of the current period including prepay, kopecks; depends on payment state."""
    full_planned_cost_rub_cents: int = 0
    """Stand-alone price of the planned period: unit price x ``periods_planned``, kopecks.

    Unlike ``full_period_cost_rub_cents`` it does not depend on what was already
    paid or on the balance. This is the number shown in "confirm start" /
    "stop server" dialogs. Do not multiply it by the term length client-side:
    ``periods_planned`` already equals the billing cycle (1 month for companies,
    the whole term for individuals).
    """
    discount_percent: int = 0
    """Discount snapshot of this act, whole percent; the only source of the percent for this act."""
    promocode_code: Optional[str] = None
    """Code of the promocode applied to this act, ``None`` if none."""
    promocode_discount_value: Optional[int] = None
    """Percent of a percentage promocode; ``None`` for no promocode or a fixed-amount one."""

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
            next_charge_rub_cents=data.get("next_charge_rub_cents", 0) or 0,
            full_period_cost_rub_cents=data.get("full_period_cost_rub_cents", 0) or 0,
            full_planned_cost_rub_cents=data.get("full_planned_cost_rub_cents", 0) or 0,
            discount_percent=data.get("discount_percent", 0) or 0,
            promocode_code=_get(data, "promocode_code"),
            promocode_discount_value=_get(data, "promocode_discount_value"),
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
class ColdStorage:
    """Current cold-storage parameters of a server whose compute was released.

    ``None`` on any server that is not in cold storage. Also ``None`` on a cold
    server without an open cold-storage act (a server-side inconsistency the API
    deliberately does not paper over with invented numbers).
    """

    act_id: int
    started_at: Optional[str] = None
    storage_gb: Optional[str] = None
    """Volume size as a decimal string (``"50.000"``), kept as a string to avoid float drift."""
    monthly_price_rub_cents: int = 0
    accrued_debt_rub_cents: int = 0
    """Storage debt accumulated so far, live value at the moment of the request."""
    billed_until_dt: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ColdStorage:
        return cls(
            act_id=data.get("act_id", 0) or 0,
            started_at=_get(data, "started_at"),
            storage_gb=_get(data, "storage_gb"),
            monthly_price_rub_cents=data.get("monthly_price_rub_cents", 0) or 0,
            accrued_debt_rub_cents=data.get("accrued_debt_rub_cents", 0) or 0,
            billed_until_dt=_get(data, "billed_until_dt"),
        )


@dataclass(frozen=True)
class ColdFreeWindow:
    """Free storage window of a stopped server: until when, and the price after.

    ``None`` when the window does not apply. ``free_until_dt`` may already be
    in the past: the window is over and the hourly billing run has not caught
    up yet, so show "free storage ended, billing starts within the hour", not
    a negative countdown.
    """

    free_until_dt: Optional[str] = None
    storage_gb: Optional[str] = None
    """Boot volume size as a decimal string; ``None`` when it cannot be determined."""
    hour_price_rub_cents: int = 0
    month_price_rub_cents: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ColdFreeWindow:
        return cls(
            free_until_dt=_get(data, "free_until_dt"),
            storage_gb=_get(data, "storage_gb"),
            hour_price_rub_cents=data.get("hour_price_rub_cents", 0) or 0,
            month_price_rub_cents=data.get("month_price_rub_cents", 0) or 0,
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
    queue_disabled: bool = False
    """This server's GPU is leased out long-term — queueing for it is refused."""
    suggested_alternative: Optional[FlavorSubstitution] = None
    """Replacement card offered when ``queue_disabled`` and capacity is zero."""
    password_rotation: Optional[PasswordRotation] = None
    """Set when the root password was rotated (or the rotation failed)."""
    maintenance_reason: Optional[str] = None
    """Customer-facing maintenance reason; ``None`` means the default wording."""
    migration_error: Optional[str] = None
    """Last migration error text; set when automatic start attempts were exhausted, else ``None``."""

    # --- Cold storage (DSD-013 / DSD-024) ---
    #
    # A stopped server keeps its boot volume for free for a while, then the
    # compute is released and the volume is billed as cold storage; with a zero
    # balance a grace period starts after which the volume is deleted. The two
    # nested blocks are mutually exclusive views "before" (``cold_free``) and
    # "after" (``cold_storage``) of the same shape; both are ``None`` for a
    # running server.
    cold_storage_since: Optional[str] = None
    """ISO datetime when the server entered cold storage; ``None`` otherwise."""
    cold_storage_planned_at: Optional[str] = None
    """Estimated ISO datetime of the move to cold storage (never in the past); ``None`` if not planned."""
    days_idle: Optional[int] = None
    """Full days the stopped server has been idle; ``None`` for a running server."""
    cold_grace_deadline: Optional[str] = None
    """ISO deadline after which the volume is deleted; only in ``ServerState.COLD_GRACE``."""
    cold_storage: Optional[ColdStorage] = None
    """Current storage parameters; only while in cold storage."""
    cold_free: Optional[ColdFreeWindow] = None
    """Free storage window of a stopped server; ``None`` when not applicable."""
    resume_usage_act: Optional[UsageAct] = None
    """What resuming this cold server would cost (unsaved act at the current plan); only for cold servers."""

    # --- Rental term (pricing-plans revision, MIAN-414/415) ---
    #
    # All read-only on the server. The five ``term_*`` snapshot fields are a
    # copy of the contract conditions taken when the term started, not a
    # derivative of ``price_plan``: the plan can be changed later, the running
    # term keeps its conditions. ``term_state`` and the ``is_*`` / ``*_pending``
    # / ``*_available`` flags are the server's own classification of that
    # snapshot; do not re-derive them client-side from the dates.
    term_months: int = 0
    """Commitment length in months; ``0`` means no commitment (hourly / postpaid)."""
    term_discount_percent: int = 0
    """Discount snapshot for the term, whole percent. Independent of the live price list."""
    term_started_at: Optional[str] = None
    """ISO datetime when the term started; ``None`` until the first usage act."""
    term_ends_at: Optional[str] = None
    """Effective end of the term, ISO datetime, already shifted by outages on our side."""
    term_conditions_accepted_at: Optional[str] = None
    """When the customer accepted the early-termination recalculation terms; ``None`` = never."""
    has_term_snapshot: bool = False
    """The snapshot above applies to the current ``price_plan``."""
    is_renewal_mandatory: bool = False
    """Term is running and was confirmed: auto-renewal cannot be switched off."""
    requires_term_consent: bool = False
    """Starting the server will open a new term, consent must be collected first."""
    term_renewal_accepted_at: Optional[str] = None
    """Customer clicked "renew on the same terms"; the new term starts when the current one ends."""
    term_outage_shift_hours: int = 0
    """Whole hours of downtime on our side already added to ``term_ends_at``."""
    term_outage_active: bool = False
    """The server is down on our side right now and ``term_ends_at`` keeps moving forward."""
    term_state: str = ""
    """One of :class:`intelion_cloud.constants.TermState`; ``""`` when the server predates the reform."""
    is_bound_by_term: bool = False
    """Stopping the rental early triggers recalculation without the term discount."""
    term_renewal_available: bool = False
    """The renewal window is open right now. Renewal itself is a personal-account action, not API v2."""
    term_renewal_pending: bool = False
    """A renewal was accepted and waits for the current term to end."""
    billing_cycle_months: int = 0
    """Months charged and frozen per payment: ``1`` for companies, the whole term for individuals."""

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
            queue_disabled=bool(data.get("queue_disabled", False)),
            suggested_alternative=_parse_nested(
                data, "suggested_alternative", FlavorSubstitution
            ),
            password_rotation=_parse_nested(data, "password_rotation", PasswordRotation),
            maintenance_reason=_get(data, "maintenance_reason"),
            migration_error=_get(data, "migration_error"),
            cold_storage_since=_get(data, "cold_storage_since"),
            cold_storage_planned_at=_get(data, "cold_storage_planned_at"),
            days_idle=_get(data, "days_idle"),
            cold_grace_deadline=_get(data, "cold_grace_deadline"),
            cold_storage=_parse_nested(data, "cold_storage", ColdStorage),
            cold_free=_parse_nested(data, "cold_free", ColdFreeWindow),
            resume_usage_act=_parse_nested(data, "resume_usage_act", UsageAct),
            term_months=data.get("term_months", 0) or 0,
            term_discount_percent=data.get("term_discount_percent", 0) or 0,
            term_started_at=_get(data, "term_started_at"),
            term_ends_at=_get(data, "term_ends_at"),
            term_conditions_accepted_at=_get(data, "term_conditions_accepted_at"),
            has_term_snapshot=bool(data.get("has_term_snapshot", False)),
            is_renewal_mandatory=bool(data.get("is_renewal_mandatory", False)),
            requires_term_consent=bool(data.get("requires_term_consent", False)),
            term_renewal_accepted_at=_get(data, "term_renewal_accepted_at"),
            term_outage_shift_hours=data.get("term_outage_shift_hours", 0) or 0,
            term_outage_active=bool(data.get("term_outage_active", False)),
            term_state=data.get("term_state", "") or "",
            is_bound_by_term=bool(data.get("is_bound_by_term", False)),
            term_renewal_available=bool(data.get("term_renewal_available", False)),
            term_renewal_pending=bool(data.get("term_renewal_pending", False)),
            billing_cycle_months=data.get("billing_cycle_months", 0) or 0,
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
