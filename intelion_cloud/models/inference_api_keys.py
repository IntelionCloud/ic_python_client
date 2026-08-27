"""AI API key management models (ТЗ §5 — inference-api-keys resource)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ._base import _get, _parse_nested, _parse_nested_list


@dataclass(frozen=True)
class InferenceApiKey:
    """An AI API key — returned by list/create/update/rotate.

    ``api_key`` is the raw secret value: present ONLY on create/rotate
    responses (and only when ``save_to_secrets_manager`` wasn't used), shown
    exactly once. ``key_hash`` (== ``id``) is the permanent, non-secret
    identifier used everywhere else (get/update/revoke/rotate/usage).
    """

    key_hash: str
    name: str
    prefix: str
    rate_limit_rpm: int
    is_active: bool
    disabled_reason: str = ""
    credit_limit_rub_cents: Optional[int] = None
    spent_rub_cents: int = 0
    free_tokens_consumed: int = 0
    limit_reset_period: str = ""
    allowed_models: Optional[List[str]] = None
    compaction_enabled: bool = True
    residency: str = ""
    expires_at: Optional[str] = None
    created_at: Optional[str] = None
    last_used_at: Optional[str] = None
    last_request_ip: Optional[str] = None
    api_key: Optional[str] = None
    saved_to_secrets_manager: bool = False
    secret_name: Optional[str] = None
    partial: bool = False
    failed_regions: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InferenceApiKey:
        return cls(
            key_hash=data.get("key_hash") or data.get("id", ""),
            name=data.get("name", ""),
            prefix=data.get("prefix", ""),
            rate_limit_rpm=data.get("rate_limit_rpm", 0),
            is_active=bool(data.get("is_active", False)),
            disabled_reason=data.get("disabled_reason", ""),
            credit_limit_rub_cents=_get(data, "credit_limit_rub_cents"),
            spent_rub_cents=data.get("spent_rub_cents", 0),
            free_tokens_consumed=data.get("free_tokens_consumed", 0),
            limit_reset_period=data.get("limit_reset_period", ""),
            allowed_models=_get(data, "allowed_models"),
            compaction_enabled=bool(data.get("compaction_enabled", True)),
            residency=data.get("residency", ""),
            expires_at=_get(data, "expires_at"),
            created_at=_get(data, "created_at"),
            last_used_at=_get(data, "last_used_at"),
            last_request_ip=_get(data, "last_request_ip"),
            api_key=_get(data, "api_key"),
            saved_to_secrets_manager=bool(data.get("saved_to_secrets_manager", False)),
            secret_name=_get(data, "secret_name"),
            partial=bool(data.get("partial", False)),
            failed_regions=list(data.get("failed_regions") or []),
        )


@dataclass(frozen=True)
class RotatedInferenceApiKey:
    """Result of ``rotate()`` — the freshly minted key plus what happened to
    the old one (still valid until ``old_expires_at``, unless
    ``grace_period_hours=0`` was requested)."""

    new_key: InferenceApiKey
    old_key_hash: str
    old_name: str
    old_expires_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RotatedInferenceApiKey:
        old = data.get("old_key") or {}
        return cls(
            new_key=InferenceApiKey.from_dict(data),
            old_key_hash=old.get("key_hash", ""),
            old_name=old.get("name", ""),
            old_expires_at=_get(old, "expires_at"),
        )


@dataclass(frozen=True)
class InferenceApiTopModel:
    """One row of a usage window's ``top_models`` breakdown."""

    model_slug: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_rub_cents: int = 0
    request_count: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InferenceApiTopModel:
        return cls(
            model_slug=data.get("model_slug", ""),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            cost_rub_cents=data.get("cost_rub_cents", 0),
            request_count=data.get("request_count", 0),
        )


@dataclass(frozen=True)
class InferenceApiUsageWindow:
    """A ``7d``/``30d`` window inside ``usage(key_hash)``."""

    input_tokens: int = 0
    output_tokens: int = 0
    cost_rub_cents: int = 0
    request_count: int = 0
    top_models: List[InferenceApiTopModel] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InferenceApiUsageWindow:
        return cls(
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            cost_rub_cents=data.get("cost_rub_cents", 0),
            request_count=data.get("request_count", 0),
            top_models=_parse_nested_list(data, "top_models", InferenceApiTopModel),
        )


@dataclass(frozen=True)
class InferenceApiKeyUsage:
    """``GET .../<key_hash>/usage/`` — per-key spend, aggregated across regions."""

    key_hash: str
    spent_rub_cents: int = 0
    free_tokens_consumed: int = 0
    window_7d: Optional[InferenceApiUsageWindow] = None
    window_30d: Optional[InferenceApiUsageWindow] = None
    partial: bool = False
    failed_regions: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InferenceApiKeyUsage:
        return cls(
            key_hash=data.get("key_hash", ""),
            spent_rub_cents=data.get("spent_rub_cents", 0),
            free_tokens_consumed=data.get("free_tokens_consumed", 0),
            window_7d=_parse_nested(data, "7d", InferenceApiUsageWindow),
            window_30d=_parse_nested(data, "30d", InferenceApiUsageWindow),
            partial=bool(data.get("partial", False)),
            failed_regions=list(data.get("failed_regions") or []),
        )


@dataclass(frozen=True)
class InferenceApiAccessStatus:
    """``GET/POST .../access/`` — AI API self-serve gate status."""

    granted: bool
    threshold_rub_cents: int
    visible_balance_rub_cents: Optional[int] = None
    shortfall_rub_cents: Optional[int] = None
    already_granted: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InferenceApiAccessStatus:
        return cls(
            granted=bool(data.get("granted", False)),
            threshold_rub_cents=data.get("threshold_rub_cents", 0),
            visible_balance_rub_cents=_get(data, "visible_balance_rub_cents"),
            shortfall_rub_cents=_get(data, "shortfall_rub_cents"),
            already_granted=bool(data.get("already_granted", False)),
        )


@dataclass(frozen=True)
class InferenceApiUsageRangeRow:
    """One flat row of ``usage_range()`` — a (key × model × day) or a
    re-grouped bucket, depending on the ``group_by`` argument."""

    billed_rub_cents: int = 0
    key_hash: Optional[str] = None
    key_name: Optional[str] = None
    is_active: Optional[bool] = None
    deleted: Optional[bool] = None
    model_slug: Optional[str] = None
    display_name: Optional[str] = None
    kind: Optional[str] = None
    date: Optional[str] = None
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    free_tokens_consumed: int = 0
    count: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InferenceApiUsageRangeRow:
        return cls(
            billed_rub_cents=data.get("billed_rub_cents", 0),
            key_hash=_get(data, "key_hash"),
            key_name=_get(data, "key_name"),
            is_active=data.get("is_active"),
            deleted=data.get("deleted"),
            model_slug=_get(data, "model_slug"),
            display_name=_get(data, "display_name"),
            kind=_get(data, "kind"),
            date=_get(data, "date"),
            requests=data.get("requests", 0),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            cache_creation_tokens=data.get("cache_creation_tokens", 0),
            cache_read_tokens=data.get("cache_read_tokens", 0),
            free_tokens_consumed=data.get("free_tokens_consumed", 0),
            count=_get(data, "count"),
        )


@dataclass(frozen=True)
class InferenceApiUsageRange:
    """``GET .../usage-range/`` — billing statistics for an arbitrary date
    range (ТЗ §3). ``total_rub_cents`` reconciles with «История операций»
    for the same range."""

    date_from: str
    date_to: str
    total_rub_cents: int
    rows: List[InferenceApiUsageRangeRow] = field(default_factory=list)
    from_local_acts: bool = False
    partial: bool = False
    failed_regions: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InferenceApiUsageRange:
        return cls(
            date_from=data.get("date_from", ""),
            date_to=data.get("date_to", ""),
            total_rub_cents=data.get("total_rub_cents", 0),
            rows=_parse_nested_list(data, "rows", InferenceApiUsageRangeRow),
            from_local_acts=bool(data.get("from_local_acts", False)),
            partial=bool(data.get("partial", False)),
            failed_regions=list(data.get("failed_regions") or []),
        )
