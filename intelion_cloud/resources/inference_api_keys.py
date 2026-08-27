"""AI API key management — list/create/update/revoke/rotate + usage + the
self-serve access gate (ТЗ ``tz-public-key-management-api.md``).

Not the same thing as the client's main API token (``Authorization: Token``,
used for every ``/api/v2/`` call including these) — these are separate
keys that authenticate against ``https://aiapi.intelion.cloud/v1/...`` for
LLM inference. See ``docs``/README for the distinction.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..models.inference_api_keys import (
    InferenceApiAccessStatus,
    InferenceApiKey,
    InferenceApiKeyUsage,
    InferenceApiUsageRange,
    RotatedInferenceApiKey,
)
from ._base import AsyncResource, SyncResource

_PATH = "inference-api-keys/"


def _create_payload(
    *, name, rate_limit_rpm, credit_limit_rub_cents, allowed_models,
    expires_at, limit_reset_period, compaction_enabled, residency,
    regions, save_to_secrets_manager,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "name": name,
        "rate_limit_rpm": rate_limit_rpm,
        "compaction_enabled": compaction_enabled,
        "residency": residency,
        "save_to_secrets_manager": save_to_secrets_manager,
    }
    if credit_limit_rub_cents is not None:
        payload["credit_limit_rub_cents"] = credit_limit_rub_cents
    if allowed_models is not None:
        payload["allowed_models"] = allowed_models
    if expires_at is not None:
        payload["expires_at"] = expires_at
    if limit_reset_period is not None:
        payload["limit_reset_period"] = limit_reset_period
    if regions is not None:
        payload["regions"] = regions
    return payload


def _update_payload(**fields: Any) -> Dict[str, Any]:
    """Only fields the caller actually passed (not None) go in the PATCH
    body — matches the server's partial-update semantics."""
    return {k: v for k, v in fields.items() if v is not None}


class InferenceApiKeys(SyncResource):
    """Synchronous AI API key management."""

    def list(self, *, include_inactive: bool = False) -> List[InferenceApiKey]:
        """List keys, merged across regions (not paginated — the wire
        contract here is a plain array, see server docstring)."""
        params = {"include_inactive": "true"} if include_inactive else None
        data = self._get(_PATH, params=params)
        return [InferenceApiKey.from_dict(row) for row in data]

    def get(self, key_hash: str) -> InferenceApiKey:
        """Fetch a single key by ``key_hash``.

        The server has no single-key GET endpoint — this is
        ``list(include_inactive=True)`` filtered client-side, i.e. an extra
        round-trip, not a dedicated call. Raises ``NotFoundError`` if no key
        with this hash exists.
        """
        from ..exceptions import NotFoundError
        for key in self.list(include_inactive=True):
            if key.key_hash == key_hash:
                return key
        raise NotFoundError("Ключ не найден", status_code=404)

    def create(
        self,
        *,
        name: str = "",
        rate_limit_rpm: int = 60,
        credit_limit_rub_cents: Optional[int] = None,
        allowed_models: Optional[List[str]] = None,
        expires_at: Optional[str] = None,
        limit_reset_period: Optional[str] = None,
        compaction_enabled: bool = True,
        residency: str = "",
        regions: Optional[List[str]] = None,
        save_to_secrets_manager: bool = False,
    ) -> InferenceApiKey:
        """Create a key. ``.api_key`` on the result is the raw secret,
        shown exactly once — persist it now. If
        ``save_to_secrets_manager=True`` and the save succeeds, ``.api_key``
        is ``None`` instead (check ``.saved_to_secrets_manager``)."""
        payload = _create_payload(
            name=name, rate_limit_rpm=rate_limit_rpm,
            credit_limit_rub_cents=credit_limit_rub_cents,
            allowed_models=allowed_models, expires_at=expires_at,
            limit_reset_period=limit_reset_period,
            compaction_enabled=compaction_enabled, residency=residency,
            regions=regions, save_to_secrets_manager=save_to_secrets_manager,
        )
        data = self._post(_PATH, json=payload)
        return InferenceApiKey.from_dict(data)

    def update(
        self,
        key_hash: str,
        *,
        name: Optional[str] = None,
        rate_limit_rpm: Optional[int] = None,
        credit_limit_rub_cents: Optional[int] = None,
        allowed_models: Optional[List[str]] = None,
        expires_at: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit_reset_period: Optional[str] = None,
        compaction_enabled: Optional[bool] = None,
        residency: Optional[str] = None,
    ) -> InferenceApiKey:
        """Partial update — only pass the fields you want to change."""
        payload = _update_payload(
            name=name, rate_limit_rpm=rate_limit_rpm,
            credit_limit_rub_cents=credit_limit_rub_cents,
            allowed_models=allowed_models, expires_at=expires_at,
            is_active=is_active, limit_reset_period=limit_reset_period,
            compaction_enabled=compaction_enabled, residency=residency,
        )
        data = self._patch(f"{_PATH}{key_hash}/", json=payload)
        return InferenceApiKey.from_dict(data)

    def revoke(self, key_hash: str) -> None:
        """Revoke (soft-delete) a key. Idempotent — revoking an
        already-revoked key is a no-op, not an error."""
        self._delete(f"{_PATH}{key_hash}/")

    def rotate(
        self,
        key_hash: str,
        *,
        grace_period_hours: int = 24,
        save_to_secrets_manager: bool = False,
    ) -> RotatedInferenceApiKey:
        """Replace the raw value under the same name/limits. The old key
        stays valid for ``grace_period_hours`` (default 24; ``0`` retires it
        immediately) — see ``.old_key_hash``/``.old_expires_at`` on the
        result. Use this instead of revoke+create to keep usage history
        attributed to one logical key across the swap."""
        payload = {
            "grace_period_hours": grace_period_hours,
            "save_to_secrets_manager": save_to_secrets_manager,
        }
        data = self._post(f"{_PATH}{key_hash}/rotate/", json=payload)
        return RotatedInferenceApiKey.from_dict(data)

    def usage(self, key_hash: str) -> InferenceApiKeyUsage:
        """Per-key spend (7d/30d windows), aggregated across regions."""
        data = self._get(f"{_PATH}{key_hash}/usage/")
        return InferenceApiKeyUsage.from_dict(data)

    def usage_range(
        self, *, date_from: str, date_to: str, group_by: str = "key",
    ) -> InferenceApiUsageRange:
        """Billing statistics for an arbitrary date range (``YYYY-MM-DD``,
        inclusive both ends, ≤ 366 days). ``group_by`` is ``"key"``
        (default), ``"model"``, or ``"day"``. ``total_rub_cents`` reconciles
        with «История операций» for the same range."""
        data = self._get(f"{_PATH}usage-range/", params={
            "date_from": date_from, "date_to": date_to, "group_by": group_by,
        })
        return InferenceApiUsageRange.from_dict(data)

    def usage_range_csv(
        self, *, date_from: str, date_to: str, group_by: str = "key",
    ) -> str:
        """Same data as ``usage_range()``, as a CSV string (UTF-8 with BOM,
        Excel-friendly). A separate method rather than a ``format=`` flag on
        ``usage_range()`` because the return type genuinely differs (``str``
        vs. a typed object)."""
        return self._get_text(f"{_PATH}usage-range/", params={
            "date_from": date_from, "date_to": date_to,
            "group_by": group_by, "format": "csv",
        })

    def models(self) -> List[Dict[str, Any]]:
        """AI API model catalog — slug, prices, context length. Raw dicts
        (same rows the ЛК ``/prices/`` page renders); no dedicated model
        class since this endpoint isn't part of the key CRUD contract."""
        return self._get(f"{_PATH}models/")

    def access_status(self) -> InferenceApiAccessStatus:
        """Read-only: is the AI API self-serve gate open, and how much
        balance is missing if not. Never opens the gate — see
        ``request_access()``."""
        data = self._get(f"{_PATH}access/")
        return InferenceApiAccessStatus.from_dict(data)

    def request_access(self) -> InferenceApiAccessStatus:
        """Open the AI API gate if the account's visible balance meets
        ``threshold_rub_cents``. Idempotent once granted. Raises
        ``PaymentRequiredError`` (402) if the balance isn't there yet —
        catch it and read ``.response_body["shortfall_rub_cents"]``."""
        data = self._post(f"{_PATH}access/")
        return InferenceApiAccessStatus.from_dict(data)


class AsyncInferenceApiKeys(AsyncResource):
    """Asynchronous AI API key management — same contract as ``InferenceApiKeys``."""

    async def list(self, *, include_inactive: bool = False) -> List[InferenceApiKey]:
        params = {"include_inactive": "true"} if include_inactive else None
        data = await self._get(_PATH, params=params)
        return [InferenceApiKey.from_dict(row) for row in data]

    async def get(self, key_hash: str) -> InferenceApiKey:
        from ..exceptions import NotFoundError
        for key in await self.list(include_inactive=True):
            if key.key_hash == key_hash:
                return key
        raise NotFoundError("Ключ не найден", status_code=404)

    async def create(
        self,
        *,
        name: str = "",
        rate_limit_rpm: int = 60,
        credit_limit_rub_cents: Optional[int] = None,
        allowed_models: Optional[List[str]] = None,
        expires_at: Optional[str] = None,
        limit_reset_period: Optional[str] = None,
        compaction_enabled: bool = True,
        residency: str = "",
        regions: Optional[List[str]] = None,
        save_to_secrets_manager: bool = False,
    ) -> InferenceApiKey:
        payload = _create_payload(
            name=name, rate_limit_rpm=rate_limit_rpm,
            credit_limit_rub_cents=credit_limit_rub_cents,
            allowed_models=allowed_models, expires_at=expires_at,
            limit_reset_period=limit_reset_period,
            compaction_enabled=compaction_enabled, residency=residency,
            regions=regions, save_to_secrets_manager=save_to_secrets_manager,
        )
        data = await self._post(_PATH, json=payload)
        return InferenceApiKey.from_dict(data)

    async def update(
        self,
        key_hash: str,
        *,
        name: Optional[str] = None,
        rate_limit_rpm: Optional[int] = None,
        credit_limit_rub_cents: Optional[int] = None,
        allowed_models: Optional[List[str]] = None,
        expires_at: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit_reset_period: Optional[str] = None,
        compaction_enabled: Optional[bool] = None,
        residency: Optional[str] = None,
    ) -> InferenceApiKey:
        payload = _update_payload(
            name=name, rate_limit_rpm=rate_limit_rpm,
            credit_limit_rub_cents=credit_limit_rub_cents,
            allowed_models=allowed_models, expires_at=expires_at,
            is_active=is_active, limit_reset_period=limit_reset_period,
            compaction_enabled=compaction_enabled, residency=residency,
        )
        data = await self._patch(f"{_PATH}{key_hash}/", json=payload)
        return InferenceApiKey.from_dict(data)

    async def revoke(self, key_hash: str) -> None:
        await self._delete(f"{_PATH}{key_hash}/")

    async def rotate(
        self,
        key_hash: str,
        *,
        grace_period_hours: int = 24,
        save_to_secrets_manager: bool = False,
    ) -> RotatedInferenceApiKey:
        payload = {
            "grace_period_hours": grace_period_hours,
            "save_to_secrets_manager": save_to_secrets_manager,
        }
        data = await self._post(f"{_PATH}{key_hash}/rotate/", json=payload)
        return RotatedInferenceApiKey.from_dict(data)

    async def usage(self, key_hash: str) -> InferenceApiKeyUsage:
        data = await self._get(f"{_PATH}{key_hash}/usage/")
        return InferenceApiKeyUsage.from_dict(data)

    async def usage_range(
        self, *, date_from: str, date_to: str, group_by: str = "key",
    ) -> InferenceApiUsageRange:
        data = await self._get(f"{_PATH}usage-range/", params={
            "date_from": date_from, "date_to": date_to, "group_by": group_by,
        })
        return InferenceApiUsageRange.from_dict(data)

    async def usage_range_csv(
        self, *, date_from: str, date_to: str, group_by: str = "key",
    ) -> str:
        return await self._get_text(f"{_PATH}usage-range/", params={
            "date_from": date_from, "date_to": date_to,
            "group_by": group_by, "format": "csv",
        })

    async def models(self) -> List[Dict[str, Any]]:
        return await self._get(f"{_PATH}models/")

    async def access_status(self) -> InferenceApiAccessStatus:
        data = await self._get(f"{_PATH}access/")
        return InferenceApiAccessStatus.from_dict(data)

    async def request_access(self) -> InferenceApiAccessStatus:
        data = await self._post(f"{_PATH}access/")
        return InferenceApiAccessStatus.from_dict(data)
