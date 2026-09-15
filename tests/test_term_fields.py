"""Rental-term fields of ``UserConfigurationSerializer`` (pricing-plans revision).

Server-side source: ``UserConfigurationSerializer`` in
``website/user_panel/serializers.py`` (branch ``feature/pricing-plans-revision``),
sixteen read-only fields: five ``term_*`` snapshot fields, the outage shift,
the server-computed ``term_state`` / ``is_*`` / ``*_pending`` / ``*_available``
flags and ``billing_cycle_months``.

Shapes are asserted against the serializer, not the OpenAPI schema:
``term_ends_at``, ``requires_term_consent`` and ``term_renewal_available`` are
``SerializerMethodField`` and drf-spectacular reports all three as ``string``,
while they are a nullable datetime and two booleans.
"""

import pytest

from intelion_cloud import TermState
from intelion_cloud.models import CloudServer

from .conftest import SAMPLE_CLOUD_SERVER, SAMPLE_TERM_SERVER

TERM_FIELDS = (
    "term_months",
    "term_discount_percent",
    "term_started_at",
    "term_ends_at",
    "term_conditions_accepted_at",
    "has_term_snapshot",
    "is_renewal_mandatory",
    "requires_term_consent",
    "term_renewal_accepted_at",
    "term_outage_shift_hours",
    "term_outage_active",
    "term_state",
    "is_bound_by_term",
    "term_renewal_available",
    "term_renewal_pending",
    "billing_cycle_months",
)


def _server(**extra):
    base = {
        "id": 8564,
        "name": "srv",
        "status": 2,
        "price_plan": 12,
        "is_auto_renewal": True,
        "monthly_price_rub_cents": 100,
        "hourly_price_rub_cents": 1,
        "server_full_rent_price_rub_cents": 100,
    }
    base.update(extra)
    return CloudServer.from_dict(base)


class TestTermFieldsPresent:
    def test_all_sixteen_fields_are_read(self):
        """Every field the serializer emits lands on the model with the same value."""
        srv = CloudServer.from_dict(SAMPLE_TERM_SERVER)
        for name in TERM_FIELDS:
            assert getattr(srv, name) == SAMPLE_TERM_SERVER[name], name

    def test_confirmed_active_term(self):
        srv = CloudServer.from_dict(SAMPLE_TERM_SERVER)
        assert srv.term_months == 12
        assert srv.term_discount_percent == 35
        assert srv.term_started_at == "2026-09-01T00:00:00+03:00"
        # Effective end already includes the 5 settled outage hours
        assert srv.term_ends_at == "2027-09-01T05:00:00+03:00"
        assert srv.term_outage_shift_hours == 5
        assert srv.term_outage_active is False
        assert srv.term_conditions_accepted_at == "2026-08-31T18:30:00+03:00"
        assert srv.term_state == TermState.ACTIVE
        assert srv.has_term_snapshot is True
        assert srv.is_renewal_mandatory is True
        assert srv.is_bound_by_term is True
        assert srv.requires_term_consent is False
        assert srv.term_renewal_pending is False
        assert srv.term_renewal_available is False
        assert srv.billing_cycle_months == 1

    def test_hourly_server_has_no_commitment(self):
        srv = CloudServer.from_dict(SAMPLE_CLOUD_SERVER)
        assert srv.term_state == TermState.NOT_TERM_PLAN
        assert srv.term_months == 0
        assert srv.term_discount_percent == 0
        assert srv.term_started_at is None
        assert srv.term_ends_at is None
        assert srv.has_term_snapshot is False
        assert srv.is_bound_by_term is False
        assert srv.is_renewal_mandatory is False
        # An hourly plan is still charged one month at a time
        assert srv.billing_cycle_months == 1

    def test_pending_consent_before_first_start(self):
        """Consent given, dates not set yet: the first usage act starts the term."""
        srv = _server(
            term_months=12,
            term_discount_percent=35,
            term_started_at=None,
            term_ends_at=None,
            term_conditions_accepted_at="2026-09-10T12:00:00+03:00",
            has_term_snapshot=True,
            term_state="pending_consent",
            is_bound_by_term=True,
            is_renewal_mandatory=False,
            requires_term_consent=False,
        )
        assert srv.term_state == TermState.PENDING_CONSENT
        assert srv.term_ends_at is None
        assert srv.is_bound_by_term is True
        assert srv.is_renewal_mandatory is False
        assert srv.requires_term_consent is False

    def test_requires_consent_on_next_start(self):
        srv = _server(term_state="confirmed_expired", requires_term_consent=True)
        assert srv.term_state == TermState.CONFIRMED_EXPIRED
        assert srv.requires_term_consent is True

    def test_open_outage_moves_the_end(self):
        srv = _server(term_outage_active=True, term_outage_shift_hours=0)
        assert srv.term_outage_active is True
        assert srv.term_outage_shift_hours == 0

    def test_renewal_window_and_pending_renewal(self):
        window_open = _server(term_renewal_available=True, term_renewal_pending=False)
        assert window_open.term_renewal_available is True
        assert window_open.term_renewal_pending is False

        renewed = _server(
            term_renewal_available=False,
            term_renewal_pending=True,
            term_renewal_accepted_at="2027-08-20T09:00:00+03:00",
        )
        assert renewed.term_renewal_pending is True
        assert renewed.term_renewal_accepted_at == "2027-08-20T09:00:00+03:00"

    def test_individual_pays_the_whole_term_upfront(self):
        srv = _server(term_months=12, billing_cycle_months=12)
        assert srv.billing_cycle_months == 12
        assert srv.billing_cycle_months == srv.term_months


class TestTermFieldsAbsentOrNull:
    def test_absent_fields_do_not_break_old_payloads(self):
        """A server that predates the reform: nothing crashes, defaults are neutral."""
        srv = _server()
        assert srv.term_months == 0
        assert srv.term_discount_percent == 0
        assert srv.term_started_at is None
        assert srv.term_ends_at is None
        assert srv.term_conditions_accepted_at is None
        assert srv.term_renewal_accepted_at is None
        assert srv.term_outage_shift_hours == 0
        assert srv.term_outage_active is False
        assert srv.has_term_snapshot is False
        assert srv.is_renewal_mandatory is False
        assert srv.requires_term_consent is False
        assert srv.is_bound_by_term is False
        assert srv.term_renewal_available is False
        assert srv.term_renewal_pending is False
        assert srv.billing_cycle_months == 0

    def test_absent_term_state_is_empty_not_a_code(self):
        """No guessing: an old server did not say, so the client does not invent a state."""
        srv = _server()
        assert srv.term_state == ""
        assert srv.term_state != TermState.NOT_TERM_PLAN

    def test_null_datetimes_stay_none(self):
        srv = _server(
            term_started_at=None,
            term_ends_at=None,
            term_conditions_accepted_at=None,
            term_renewal_accepted_at=None,
        )
        assert srv.term_started_at is None
        assert srv.term_ends_at is None
        assert srv.term_conditions_accepted_at is None
        assert srv.term_renewal_accepted_at is None

    def test_empty_string_datetimes_normalised_to_none(self):
        srv = _server(term_started_at="", term_ends_at="")
        assert srv.term_started_at is None
        assert srv.term_ends_at is None

    def test_null_numbers_and_state_fall_back_to_defaults(self):
        srv = _server(
            term_months=None,
            term_discount_percent=None,
            term_outage_shift_hours=None,
            billing_cycle_months=None,
            term_state=None,
        )
        assert srv.term_months == 0
        assert srv.term_discount_percent == 0
        assert srv.term_outage_shift_hours == 0
        assert srv.billing_cycle_months == 0
        assert srv.term_state == ""

    @pytest.mark.parametrize(
        "flag",
        [
            "has_term_snapshot",
            "is_renewal_mandatory",
            "requires_term_consent",
            "term_outage_active",
            "is_bound_by_term",
            "term_renewal_available",
            "term_renewal_pending",
        ],
    )
    def test_boolean_flags_are_real_booleans(self, flag):
        """Null or a stringly-typed schema must not leak into ``if server.flag:`` checks."""
        assert getattr(_server(**{flag: None}), flag) is False
        assert getattr(_server(**{flag: True}), flag) is True
        assert getattr(_server(**{flag: False}), flag) is False


class TestTermStateConstants:
    def test_codes_match_server_consts(self):
        """``user_panel.consts.TermState`` on the server, one to one."""
        assert TermState.NOT_TERM_PLAN == "not_term_plan"
        assert TermState.ACTIVE == "active"
        assert TermState.PENDING_CONSENT == "pending_consent"
        assert TermState.GRANDFATHERED == "grandfathered"
        assert TermState.LEGACY_EXPIRED == "legacy_expired"
        assert TermState.CONFIRMED_EXPIRED == "confirmed_expired"

    def test_unknown_future_code_is_kept_verbatim(self):
        """The client must not swallow a state added on the server later."""
        assert _server(term_state="something_new").term_state == "something_new"
