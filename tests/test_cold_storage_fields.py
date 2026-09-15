"""Cold-storage fields of ``UserConfigurationSerializer`` (DSD-013 / DSD-024).

Server-side source: ``UserConfigurationSerializer`` in
``website/user_panel/serializers.py`` on ``develop``. Eight fields the SDK used
to drop: ``cold_storage_since`` (model DateTimeField), ``migration_error``
(model TextField), and six ``SerializerMethodField``:
``cold_storage_planned_at`` / ``cold_grace_deadline`` (ISO or null),
``days_idle`` (int or null), ``cold_storage`` / ``cold_free`` (nested dict or
null) and ``resume_usage_act`` (``UsageActShortSerializer`` or null).

Shapes are asserted against the serializer, not the OpenAPI schema, which
reports every one of those six as ``string``.
"""

import pytest

from intelion_cloud import ServerState
from intelion_cloud.models import CloudServer, ColdFreeWindow, ColdStorage, UsageAct

from .conftest import (
    SAMPLE_CLOUD_SERVER,
    SAMPLE_COLD_SERVER,
    SAMPLE_STOPPED_SERVER,
    SAMPLE_USAGE_ACT,
)

COLD_FIELDS = (
    "cold_storage_since",
    "cold_storage_planned_at",
    "days_idle",
    "cold_grace_deadline",
    "cold_storage",
    "cold_free",
    "resume_usage_act",
    "migration_error",
)


def _server(**extra):
    base = {
        "id": 8564,
        "name": "srv",
        "status": -1,
        "price_plan": 0,
        "is_auto_renewal": True,
        "monthly_price_rub_cents": 100,
        "hourly_price_rub_cents": 1,
        "server_full_rent_price_rub_cents": 100,
    }
    base.update(extra)
    return CloudServer.from_dict(base)


class TestColdStorageModel:
    def test_from_dict(self):
        cs = ColdStorage.from_dict(SAMPLE_COLD_SERVER["cold_storage"])
        assert cs.act_id == 777
        assert cs.started_at == "2026-09-01T12:00:00+03:00"
        # Decimal(10,3) travels as a string: no float drift on the client either
        assert cs.storage_gb == "50.000"
        assert cs.monthly_price_rub_cents == 5000
        assert cs.accrued_debt_rub_cents == 2333
        assert cs.billed_until_dt == "2026-09-15T12:00:00+03:00"

    def test_minimal_payload(self):
        cs = ColdStorage.from_dict({"act_id": 1})
        assert cs.storage_gb is None
        assert cs.monthly_price_rub_cents == 0
        assert cs.accrued_debt_rub_cents == 0
        assert cs.billed_until_dt is None


class TestColdFreeWindowModel:
    def test_from_dict(self):
        w = ColdFreeWindow.from_dict(SAMPLE_STOPPED_SERVER["cold_free"])
        assert w.free_until_dt == "2026-09-20T12:00:00+03:00"
        assert w.storage_gb == "50.000"
        assert w.hour_price_rub_cents == 7
        assert w.month_price_rub_cents == 5000

    def test_unknown_boot_volume_size(self):
        """Server sends ``storage_gb: null`` when the boot disk cannot be determined."""
        w = ColdFreeWindow.from_dict(
            {
                "free_until_dt": "2026-09-20T12:00:00+03:00",
                "storage_gb": None,
                "hour_price_rub_cents": 0,
                "month_price_rub_cents": 0,
            }
        )
        assert w.storage_gb is None
        assert w.hour_price_rub_cents == 0

    def test_free_window_already_over_is_kept_as_is(self):
        """``free_until_dt`` in the past means billing starts within the hour; not normalised away."""
        w = ColdFreeWindow.from_dict({"free_until_dt": "2020-01-01T00:00:00+03:00"})
        assert w.free_until_dt == "2020-01-01T00:00:00+03:00"


class TestCloudServerColdFields:
    def test_running_server_has_no_cold_data(self):
        srv = CloudServer.from_dict(SAMPLE_CLOUD_SERVER)
        for name in COLD_FIELDS:
            assert getattr(srv, name) is None, name

    def test_stopped_server_inside_free_window(self):
        srv = CloudServer.from_dict(SAMPLE_STOPPED_SERVER)
        assert srv.days_idle == 9
        assert srv.cold_storage_planned_at == "2026-09-20T12:00:00+03:00"
        assert isinstance(srv.cold_free, ColdFreeWindow)
        assert srv.cold_free.hour_price_rub_cents == 7
        # "before" and "after" blocks are mutually exclusive
        assert srv.cold_storage is None
        assert srv.cold_storage_since is None
        assert srv.resume_usage_act is None
        assert srv.server_state == ServerState.IDLE

    def test_cold_server(self):
        srv = CloudServer.from_dict(SAMPLE_COLD_SERVER)
        assert srv.server_state == ServerState.COLD_STORAGE
        assert srv.has_instance is False
        assert srv.cold_storage_since == "2026-09-01T12:00:00+03:00"
        assert srv.days_idle == 30
        assert isinstance(srv.cold_storage, ColdStorage)
        assert srv.cold_storage.act_id == 777
        assert srv.cold_storage.accrued_debt_rub_cents == 2333
        assert srv.cold_free is None
        assert srv.cold_storage_planned_at is None
        assert srv.cold_grace_deadline is None
        # Resume price comes from the server as a usage act, same model as usage_act
        assert isinstance(srv.resume_usage_act, UsageAct)
        assert srv.resume_usage_act.id == SAMPLE_USAGE_ACT["id"]
        assert srv.resume_usage_act.next_payment is not None
        assert srv.resume_usage_act.next_payment.amount_rub_cents == 16071
        # The running-rental act is not faked for a cold server
        assert srv.usage_act is None

    def test_cold_grace_has_deadline(self):
        srv = _server(
            server_state=1100,
            cold_storage_since="2026-09-01T12:00:00+03:00",
            cold_grace_deadline="2026-09-18T12:00:00+03:00",
            cold_storage=SAMPLE_COLD_SERVER["cold_storage"],
        )
        assert srv.server_state == ServerState.COLD_GRACE
        assert srv.cold_grace_deadline == "2026-09-18T12:00:00+03:00"
        assert srv.cold_storage is not None

    def test_cold_server_without_open_act_reports_no_numbers(self):
        """Server-side inconsistency (act closed, state not rolled back): ``cold_storage`` is null, not invented."""
        srv = _server(server_state=1000, cold_storage_since="2026-09-01T12:00:00+03:00", cold_storage=None)
        assert srv.server_state == ServerState.COLD_STORAGE
        assert srv.cold_storage is None

    def test_days_idle_zero_is_zero_not_none(self):
        """Stopped less than a day ago: ``0`` is a real value and must not collapse to ``None``."""
        assert _server(days_idle=0).days_idle == 0

    def test_migration_error(self):
        assert _server(migration_error="NoValidHost: 3 attempts").migration_error == "NoValidHost: 3 attempts"
        assert _server(migration_error=None).migration_error is None
        assert _server(migration_error="").migration_error is None


class TestColdFieldsAbsentOrNull:
    def test_absent_fields_do_not_break_old_payloads(self):
        srv = _server()
        for name in COLD_FIELDS:
            assert getattr(srv, name) is None, name

    def test_explicit_nulls(self):
        srv = _server(**{name: None for name in COLD_FIELDS})
        for name in COLD_FIELDS:
            assert getattr(srv, name) is None, name

    def test_empty_string_datetimes_normalised_to_none(self):
        srv = _server(cold_storage_since="", cold_storage_planned_at="", cold_grace_deadline="")
        assert srv.cold_storage_since is None
        assert srv.cold_storage_planned_at is None
        assert srv.cold_grace_deadline is None

    @pytest.mark.parametrize("field", ["cold_storage", "cold_free", "resume_usage_act"])
    def test_nested_block_of_wrong_shape_is_ignored(self, field):
        """A stringly-typed value (what the OpenAPI schema promises) must not crash the parser."""
        assert getattr(_server(**{field: "not-an-object"}), field) is None


class TestServerStateColdCodes:
    def test_codes_match_server_consts(self):
        """``user_panel.consts.UserConfigState`` on the server, one to one."""
        assert ServerState.CLEANUP_IN_PROGRESS == 800
        assert ServerState.REINSTALLING == 900
        assert ServerState.COLD_MOVING == 950
        assert ServerState.COLD_STORAGE == 1000
        assert ServerState.COLD_GRACE == 1100

    def test_unknown_future_state_is_kept_as_int(self):
        assert _server(server_state=1234).server_state == 1234
