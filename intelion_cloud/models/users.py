"""User model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ._base import _get


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
        )
