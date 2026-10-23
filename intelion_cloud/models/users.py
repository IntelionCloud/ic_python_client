"""User model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ._base import _get, _parse_nested


@dataclass(frozen=True)
class ColdStorageSummary:
    """Account-wide cold-storage totals for the panel header (DSD-013).

    ``User.cold_storage_summary`` is ``None`` when the client has no servers in
    cold storage. The debt is live (accrued up to the moment of the request).
    """

    servers_count: int = 0
    grace_servers_count: int = 0
    """How many of those servers are in the grace period before the volume is deleted."""
    month_price_rub_cents: int = 0
    debt_rub_cents: int = 0
    nearest_grace_deadline: Optional[str] = None
    """ISO datetime of the earliest volume deletion; ``None`` if no server is in grace."""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ColdStorageSummary:
        return cls(
            servers_count=data.get("servers_count", 0) or 0,
            grace_servers_count=data.get("grace_servers_count", 0) or 0,
            month_price_rub_cents=data.get("month_price_rub_cents", 0) or 0,
            debt_rub_cents=data.get("debt_rub_cents", 0) or 0,
            nearest_grace_deadline=_get(data, "nearest_grace_deadline"),
        )


@dataclass(frozen=True)
class User:
    """Intelion Cloud user account."""

    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    current_balance_rub_cents: int
    held_up_money_rub_cents: int
    is_phone_verified: bool
    is_staff: bool
    legal: Optional[str] = None
    company_name: str = ""
    card_number: Optional[str] = None
    invoice_requested_rub_cents: int = 0
    balance_top_up_recommend_rub_cents: int = 0
    available_top_up_rub_cents: int = 0
    identity_token: Optional[str] = None
    default_payment_type: Optional[str] = None
    tg_id: bool = False
    should_show_referral_banner: bool = False
    white_label_partner: Optional[str] = None
    phone_number: Optional[str] = None
    is_email_verified: bool = False
    account_manager: Optional[str] = None
    is_test: bool = False
    is_edo_connected: bool = False
    invalid_name: bool = False
    last_viewed_event: Optional[str] = None
    is_term_business: bool = False
    """Business customer for the term plans: a company or sole proprietor with filled-in details.

    Offer clause 8.5: a customer that has not provided its company name, INN
    and OGRN (OGRNIP) is treated as an individual. ``legal`` alone is not
    enough; a company without an INN pays the whole term upfront exactly like
    an individual. Read-only, computed on the server. This is the live
    predicate: inside a running term the snapshot on the server wins, see
    :attr:`CloudServer.pays_term_monthly`. ``False`` when the server predates
    the pricing-plans revision.
    """
    overdraft_limit_rub_cents: int = 0
    """Overdraft limit granted to the account, kopecks."""
    held_up_money_rub: float = 0.0
    """Frozen money in roubles (the same amount as ``held_up_money_rub_cents`` / 100)."""
    bonus_balance_rub_cents: int = 0
    """Bonus part of the balance, kopecks."""
    is_kyc_needed: bool = False
    has_max: bool = False
    """The account is linked to the MAX messenger."""
    is_beta_tester: bool = False
    is_access_to_aiapi_granted: bool = False
    """AI API access was opened (sticky: not revoked when the balance drops)."""
    date_joined: Optional[str] = None
    """ISO datetime of registration."""
    cold_storage_summary: Optional[ColdStorageSummary] = None
    """Cold-storage totals; ``None`` when no server is in cold storage."""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> User:
        return cls(
            id=data["id"],
            username=data.get("username", ""),
            email=data.get("email", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            current_balance_rub_cents=data.get("current_balance_rub_cents", 0),
            held_up_money_rub_cents=data.get("held_up_money_rub_cents", 0),
            is_phone_verified=data.get("is_phone_verified", False),
            is_staff=data.get("is_staff", False),
            legal=_get(data, "legal"),
            company_name=data.get("company_name", ""),
            card_number=_get(data, "card_number"),
            invoice_requested_rub_cents=data.get("invoice_requested_rub_cents", 0),
            balance_top_up_recommend_rub_cents=data.get("balance_top_up_recommend_rub_cents", 0),
            available_top_up_rub_cents=data.get("available_top_up_rub_cents", 0),
            identity_token=_get(data, "identity_token"),
            default_payment_type=_get(data, "default_payment_type"),
            tg_id=data.get("tg_id", False),
            should_show_referral_banner=data.get("should_show_referral_banner", False),
            white_label_partner=_get(data, "white_label_partner"),
            phone_number=_get(data, "phone_number"),
            is_email_verified=data.get("is_email_verified", False),
            account_manager=_get(data, "account_manager"),
            is_test=data.get("is_test", False),
            is_edo_connected=data.get("is_edo_connected", False),
            invalid_name=data.get("invalid_name", False),
            last_viewed_event=_get(data, "last_viewed_event"),
            is_term_business=bool(data.get("is_term_business", False)),
            overdraft_limit_rub_cents=data.get("overdraft_limit_rub_cents", 0) or 0,
            held_up_money_rub=data.get("held_up_money_rub", 0.0) or 0.0,
            bonus_balance_rub_cents=data.get("bonus_balance_rub_cents", 0) or 0,
            is_kyc_needed=bool(data.get("is_kyc_needed", False)),
            has_max=bool(data.get("has_max", False)),
            is_beta_tester=bool(data.get("is_beta_tester", False)),
            is_access_to_aiapi_granted=bool(data.get("is_access_to_aiapi_granted", False)),
            date_joined=_get(data, "date_joined"),
            cold_storage_summary=_parse_nested(data, "cold_storage_summary", ColdStorageSummary),
        )
