"""Fields and arguments found by the 0.7.0 comparison of the SDK with the server serializers.

The comparison (PRT-86) was made against the code of the public v2
serializers, not the OpenAPI schema: drf-spectacular types every
``SerializerMethodField`` as ``string``. Each block below covers one gap that
was found: the server sent the data and the SDK silently dropped it, or the
server accepted a request argument that the SDK could not send.

Server-side sources:

* ``UserSerializer`` (``user_panel/serializers.py``): account fields.
* ``UserConfigurationAddonSerializer`` (``addons/serializers.py``): addon log.
* ``UserConfigurationSerializer.get_cold_free`` and ``get_disk_extend_order``.
* ``retrieve_server_can_start`` (``user_panel/views/views.py``, PRT-259):
  ``upcoming_term_payment``.
* ``CreateConfigurationSerializer.ssh_key_ids``, ``ChangeConfigurationSerializer.ssd_count``.
"""

import json

import pytest
import respx

from intelion_cloud import (
    AsyncIntelionCloud,
    ColdStorageSummary,
    DiskExtendOrder,
    IntelionCloud,
    UpcomingTermPayment,
)
from intelion_cloud.models import (
    CloudServer,
    ColdFreeWindow,
    ServerStatus,
    SoftwareAddonInstance,
    User,
)

from .conftest import (
    API_URL,
    BASE_URL,
    SAMPLE_CLOUD_SERVER,
    SAMPLE_SOFTWARE_ADDON,
    SAMPLE_USER,
)

STATUS_BASE = {
    "can_start": True,
    "is_enough_money_for_full_period": 1,
    "affordable_runtime_seconds": 3600,
    "remaining_monthly_seconds": 0,
    "launch_required_rub_cents": 650_000,
    "launch_funds_rub_cents": 700_000,
}

UPCOMING = {
    "server_id": 77,
    "server_name": "train-box",
    "amount_rub_cents": 1_200_000,
    "date": "2026-11-02T09:00:00+00:00",
    "shortfall_rub_cents": 1_150_000,
}


class TestUpcomingTermPayment:
    """PRT-259: the start window learns about the neighbour's mandatory payment."""

    def test_present(self):
        status = ServerStatus.from_dict({**STATUS_BASE, "upcoming_term_payment": UPCOMING})
        payment = status.upcoming_term_payment
        assert isinstance(payment, UpcomingTermPayment)
        assert payment.server_id == 77
        assert payment.server_name == "train-box"
        assert payment.amount_rub_cents == 1_200_000
        assert payment.date == "2026-11-02T09:00:00+00:00"
        assert payment.shortfall_rub_cents == 1_150_000

    def test_null_when_no_payment(self):
        """The server sends an explicit ``null`` when nothing is unfunded."""
        status = ServerStatus.from_dict({**STATUS_BASE, "upcoming_term_payment": None})
        assert status.upcoming_term_payment is None

    def test_absent_on_older_server(self):
        status = ServerStatus.from_dict(STATUS_BASE)
        assert status.upcoming_term_payment is None

    def test_cannot_start_branch(self):
        """When ``can_start`` is false the view sends ``null`` next to the other null fields."""
        status = ServerStatus.from_dict(
            {
                "can_start": False,
                "is_enough_money_for_full_period": 0,
                "affordable_runtime_seconds": 0,
                "launch_required_rub_cents": None,
                "launch_funds_rub_cents": None,
                "upcoming_term_payment": None,
            }
        )
        assert status.can_start is False
        assert status.upcoming_term_payment is None

    @respx.mock(base_url=API_URL)
    def test_get_status_both_cases(self, respx_mock):
        route = respx_mock.get("cloud-servers/42/status/")
        route.side_effect = [
            respx.MockResponse(200, json={**STATUS_BASE, "upcoming_term_payment": UPCOMING}),
            respx.MockResponse(200, json={**STATUS_BASE, "upcoming_term_payment": None}),
        ]
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        warned = client.cloud_servers.get_status(42)
        clean = client.cloud_servers.get_status(42)
        client.close()
        assert warned.upcoming_term_payment is not None
        assert warned.upcoming_term_payment.shortfall_rub_cents == 1_150_000
        assert clean.upcoming_term_payment is None


class TestUserAccountFields:
    ACCOUNT = {
        "overdraft_limit_rub_cents": 300_000,
        "held_up_money_rub": 1000.5,
        "bonus_balance_rub_cents": 25_000,
        "is_kyc_needed": True,
        "has_max": True,
        "is_beta_tester": True,
        "is_access_to_aiapi_granted": True,
        "date_joined": "2025-03-04T10:20:30+03:00",
        "cold_storage_summary": {
            "servers_count": 3,
            "grace_servers_count": 1,
            "month_price_rub_cents": 45_000,
            "debt_rub_cents": 12_345,
            "nearest_grace_deadline": "2026-11-01T00:00:00+03:00",
        },
    }

    def test_all_fields_are_read(self):
        user = User.from_dict({**SAMPLE_USER, **self.ACCOUNT})
        assert user.overdraft_limit_rub_cents == 300_000
        assert user.held_up_money_rub == 1000.5
        assert user.bonus_balance_rub_cents == 25_000
        assert user.is_kyc_needed is True
        assert user.has_max is True
        assert user.is_beta_tester is True
        assert user.is_access_to_aiapi_granted is True
        assert user.date_joined == "2025-03-04T10:20:30+03:00"
        summary = user.cold_storage_summary
        assert isinstance(summary, ColdStorageSummary)
        assert summary.servers_count == 3
        assert summary.grace_servers_count == 1
        assert summary.month_price_rub_cents == 45_000
        assert summary.debt_rub_cents == 12_345
        assert summary.nearest_grace_deadline == "2026-11-01T00:00:00+03:00"

    def test_defaults_on_older_server(self):
        """The existing sample carries none of the new keys."""
        user = User.from_dict(SAMPLE_USER)
        assert user.overdraft_limit_rub_cents == 0
        assert user.held_up_money_rub == 0.0
        assert user.bonus_balance_rub_cents == 0
        assert user.is_kyc_needed is False
        assert user.has_max is False
        assert user.is_beta_tester is False
        assert user.is_access_to_aiapi_granted is False
        assert user.date_joined is None
        assert user.cold_storage_summary is None

    def test_no_cold_storage_means_null_summary(self):
        user = User.from_dict({**SAMPLE_USER, "cold_storage_summary": None})
        assert user.cold_storage_summary is None

    def test_summary_without_grace_has_no_deadline(self):
        """``nearest_grace_deadline`` is ``null`` when no server is in grace."""
        summary = ColdStorageSummary.from_dict(
            {
                "servers_count": 1,
                "grace_servers_count": 0,
                "month_price_rub_cents": 100,
                "debt_rub_cents": 0,
                "nearest_grace_deadline": None,
            }
        )
        assert summary.nearest_grace_deadline is None
        assert summary.debt_rub_cents == 0

    def test_explicit_nulls_do_not_crash(self):
        user = User.from_dict(
            {**SAMPLE_USER, "held_up_money_rub": None, "overdraft_limit_rub_cents": None}
        )
        assert user.held_up_money_rub == 0.0
        assert user.overdraft_limit_rub_cents == 0


class TestAddonInstanceLog:
    FAILED = {
        **SAMPLE_SOFTWARE_ADDON,
        "status": "failed",
        "error_message": "docker pull failed",
        "has_error": True,
        "slug": "comfyui",
        "last_install_log": "step 3: error\n",
        "last_install_log_kind": "install",
        "last_install_log_dt": "2026-10-20T08:00:00Z",
    }

    def test_failed_install_has_the_log(self):
        addon = SoftwareAddonInstance.from_dict(self.FAILED)
        assert addon.slug == "comfyui"
        assert addon.last_install_log == "step 3: error\n"
        assert addon.last_install_log_kind == "install"
        assert addon.last_install_log_dt == "2026-10-20T08:00:00Z"

    def test_log_is_empty_unless_failed(self):
        """The server sends an empty string for the log of a healthy install."""
        addon = SoftwareAddonInstance.from_dict(
            {
                **SAMPLE_SOFTWARE_ADDON,
                "slug": "comfyui",
                "last_install_log": "",
                "last_install_log_kind": "",
                "last_install_log_dt": None,
            }
        )
        assert addon.slug == "comfyui"
        assert addon.last_install_log == ""
        assert addon.last_install_log_kind == ""
        assert addon.last_install_log_dt is None

    def test_old_sample_without_new_keys(self):
        addon = SoftwareAddonInstance.from_dict(SAMPLE_SOFTWARE_ADDON)
        assert addon.slug == ""
        assert addon.last_install_log == ""
        assert addon.last_install_log_dt is None

    def test_nested_in_cloud_server(self):
        server = CloudServer.from_dict({**SAMPLE_CLOUD_SERVER, "software_addons": [self.FAILED]})
        assert server.software_addons[0].last_install_log == "step 3: error\n"


class TestColdFreeHours:
    def test_free_hours_is_read(self):
        window = ColdFreeWindow.from_dict(
            {
                "free_until_dt": "2026-11-01T00:00:00+03:00",
                "free_hours": 72,
                "storage_gb": "50.000",
                "hour_price_rub_cents": 5,
                "month_price_rub_cents": 3600,
            }
        )
        assert window.free_hours == 72

    def test_zero_is_not_none(self):
        assert ColdFreeWindow.from_dict({"free_hours": 0}).free_hours == 0

    def test_older_server_has_none(self):
        assert ColdFreeWindow.from_dict({"free_until_dt": "2026-11-01T00:00:00+03:00"}).free_hours is None


class TestDiskExtendOrder:
    def test_order_present(self):
        server = CloudServer.from_dict(
            {**SAMPLE_CLOUD_SERVER, "disk_extend_order": {"from_gb": 100, "to_gb": 250}}
        )
        assert isinstance(server.disk_extend_order, DiskExtendOrder)
        assert server.disk_extend_order.from_gb == 100
        assert server.disk_extend_order.to_gb == 250

    def test_no_order_is_none(self):
        server = CloudServer.from_dict({**SAMPLE_CLOUD_SERVER, "disk_extend_order": None})
        assert server.disk_extend_order is None

    def test_older_server_has_none(self):
        assert CloudServer.from_dict(SAMPLE_CLOUD_SERVER).disk_extend_order is None


class TestCreateSshKeys:
    @respx.mock(base_url=API_URL)
    def test_ssh_key_ids_are_sent(self, respx_mock):
        respx_mock.post("cloud-servers/").respond(201, json=SAMPLE_CLOUD_SERVER)
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        client.cloud_servers.create(
            name="n", flavor_id=1, ssd_count=50, os_id=1, ssh_key_ids=[3, 4]
        )
        client.close()
        assert json.loads(respx_mock.calls[0].request.content)["ssh_key_ids"] == [3, 4]

    @respx.mock(base_url=API_URL)
    def test_not_sent_by_default(self, respx_mock):
        """Empty means password only; the key is not added to the body."""
        respx_mock.post("cloud-servers/").respond(201, json=SAMPLE_CLOUD_SERVER)
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        client.cloud_servers.create(name="n", flavor_id=1, ssd_count=50, os_id=1)
        client.cloud_servers.create(
            name="n", flavor_id=1, ssd_count=50, os_id=1, ssh_key_ids=[]
        )
        client.close()
        for call in respx_mock.calls:
            assert "ssh_key_ids" not in json.loads(call.request.content)

    @pytest.mark.asyncio
    @respx.mock(base_url=API_URL)
    async def test_async_create_sends_ssh_key_ids(self, respx_mock):
        respx_mock.post("cloud-servers/").respond(201, json=SAMPLE_CLOUD_SERVER)
        client = AsyncIntelionCloud(token="tok", base_url=BASE_URL)
        await client.cloud_servers.create(
            name="n", flavor_id=1, ssd_count=50, os_id=1, ssh_key_ids=[9]
        )
        await client.close()
        assert json.loads(respx_mock.calls[0].request.content)["ssh_key_ids"] == [9]


class TestMigrateDiskSize:
    @respx.mock(base_url=API_URL)
    def test_ssd_count_is_sent(self, respx_mock):
        respx_mock.post("cloud-servers/42/migrate/").respond(200, json=SAMPLE_CLOUD_SERVER)
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        client.cloud_servers.migrate(42, flavor_id=2, price_plan=1, ssd_count=200)
        client.close()
        body = json.loads(respx_mock.calls[0].request.content)
        assert body == {"flavor_id": 2, "price_plan": 1, "ssd_count": 200}

    @respx.mock(base_url=API_URL)
    def test_not_sent_by_default(self, respx_mock):
        respx_mock.post("cloud-servers/42/migrate/").respond(200, json=SAMPLE_CLOUD_SERVER)
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        client.cloud_servers.migrate(42, flavor_id=2, price_plan=1)
        client.close()
        assert json.loads(respx_mock.calls[0].request.content) == {
            "flavor_id": 2,
            "price_plan": 1,
        }

    @pytest.mark.asyncio
    @respx.mock(base_url=API_URL)
    async def test_async_migrate_sends_ssd_count(self, respx_mock):
        respx_mock.post("cloud-servers/42/migrate/").respond(200, json=SAMPLE_CLOUD_SERVER)
        client = AsyncIntelionCloud(token="tok", base_url=BASE_URL)
        await client.cloud_servers.migrate(42, flavor_id=2, price_plan=1, ssd_count=64)
        await client.close()
        assert json.loads(respx_mock.calls[0].request.content)["ssd_count"] == 64


class TestTermConflictCodes:
    """Codes of v2 refusals that the SDK lists (values mirror ``term_obligation`` on the server)."""

    @pytest.mark.parametrize(
        "name",
        [
            "AUTO_RENEWAL_CONSENT_REQUIRED",
            "AUTO_RENEWAL_NOT_APPLICABLE",
            "AUTO_RENEWAL_PLAN_WITHDRAWN",
            "TERM_RENEWAL_IN_PROGRESS",
            "TERM_CONDITIONS_REQUIRED",
            "LEGAL_TYPE_REQUIRED",
            "LEGACY_TERMS_CONSENT_REQUIRED",
            "AFFORDABLE_LAUNCH_UNDER_TERM",
            "TERM_TERMINATION_REQUIRED",
        ],
    )
    def test_value_is_the_name(self, name):
        from intelion_cloud import TermConflictCode

        assert getattr(TermConflictCode, name) == name

    @respx.mock(base_url=API_URL)
    def test_error_code_is_read_from_the_409(self, respx_mock):
        from intelion_cloud import ConflictError, TermConflictCode

        respx_mock.post("cloud-servers/42/actions/").respond(
            409,
            json={
                "error_code": "AFFORDABLE_LAUNCH_UNDER_TERM",
                "message": "m",
                "detail": "m",
            },
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(ConflictError) as info:
            client.cloud_servers.start(42, run_on_affordable_time=True)
        client.close()
        assert info.value.error_code == TermConflictCode.AFFORDABLE_LAUNCH_UNDER_TERM
