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
)
from intelion_cloud.models import (
    CloudServer,
    ColdFreeWindow,
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
            name="n", flavor_id=1, ssd_count=128, os_id=1, ssh_key_ids=[3, 4]
        )
        client.close()
        assert json.loads(respx_mock.calls[0].request.content)["ssh_key_ids"] == [3, 4]

    @respx.mock(base_url=API_URL)
    def test_not_sent_by_default(self, respx_mock):
        """Empty means password only; the key is not added to the body."""
        respx_mock.post("cloud-servers/").respond(201, json=SAMPLE_CLOUD_SERVER)
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        client.cloud_servers.create(name="n", flavor_id=1, ssd_count=128, os_id=1)
        client.cloud_servers.create(
            name="n", flavor_id=1, ssd_count=128, os_id=1, ssh_key_ids=[]
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
            name="n", flavor_id=1, ssd_count=128, os_id=1, ssh_key_ids=[9]
        )
        await client.close()
        assert json.loads(respx_mock.calls[0].request.content)["ssh_key_ids"] == [9]


class TestMigrateDiskSize:
    @respx.mock(base_url=API_URL)
    def test_ssd_count_is_sent(self, respx_mock):
        respx_mock.post("cloud-servers/42/migrate/").respond(200, json=SAMPLE_CLOUD_SERVER)
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        client.cloud_servers.migrate(42, flavor_id=2, price_plan=1, ssd_count=256)
        client.close()
        body = json.loads(respx_mock.calls[0].request.content)
        assert body == {"flavor_id": 2, "price_plan": 1, "ssd_count": 256}

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
        await client.cloud_servers.migrate(42, flavor_id=2, price_plan=1, ssd_count=128)
        await client.close()
        assert json.loads(respx_mock.calls[0].request.content)["ssd_count"] == 128


class TestMirrorsServerConstants:
    """Values copied from ``user_panel/consts.py`` and ``term_obligation.py`` on the server (origin/main, 2026-10-23)."""

    SERVER_USER_CONFIG_STATE = {
        "IDLE": 0, "STARTING": 100, "SHELVING": 200,
        "MIGRATING_SHELVING": 301, "MIGRATING_SNAPSHOTTING": 302,
        "MIGRATING_DELETING": 303, "MIGRATING_CREATING": 304,
        "DISK_EXTENDING": 350, "DISK_EXTENDING_ON_START": 360,
        "CLONING": 400, "QUEUED": 500, "AWAITING_PASSWORD": 600,
        "MAINTENANCE": 700, "CLEANUP_IN_PROGRESS": 800, "REINSTALLING": 900,
        "COLD_MOVING": 950, "COLD_STORAGE": 1000, "COLD_GRACE": 1100,
    }
    SERVER_TERM_STATE = {
        "NOT_TERM_PLAN": "not_term_plan", "ACTIVE": "active",
        "PENDING_CONSENT": "pending_consent", "GRANDFATHERED": "grandfathered",
        "LEGACY_EXPIRED": "legacy_expired", "CONFIRMED_EXPIRED": "confirmed_expired",
        "NO_SNAPSHOT": "no_snapshot",
    }
    SERVER_TERM_CODES = {
        "AUTO_RENEWAL_CONSENT_REQUIRED": "AUTO_RENEWAL_CONSENT_REQUIRED",
        "AUTO_RENEWAL_NOT_APPLICABLE": "AUTO_RENEWAL_NOT_APPLICABLE",
        "TERM_RENEWAL_IN_PROGRESS": "TERM_RENEWAL_IN_PROGRESS",
        "TERM_CONDITIONS_REQUIRED": "TERM_CONDITIONS_REQUIRED",
        "LEGAL_TYPE_REQUIRED": "LEGAL_TYPE_REQUIRED",
        "LEGACY_TERMS_CONSENT_REQUIRED": "LEGACY_TERMS_CONSENT_REQUIRED",
        "AFFORDABLE_LAUNCH_UNDER_TERM": "AFFORDABLE_LAUNCH_UNDER_TERM",
        "TERM_TERMINATION_REQUIRED": "TERM_TERMINATION_REQUIRED",
    }

    def test_server_state_matches_server(self):
        from intelion_cloud import ServerState

        assert {m.name: m.value for m in ServerState} == self.SERVER_USER_CONFIG_STATE

    def test_disk_extending_states(self):
        from intelion_cloud import ServerState

        assert ServerState.DISK_EXTENDING == 350
        assert ServerState.DISK_EXTENDING_ON_START == 360

    def test_term_state_matches_server(self):
        from intelion_cloud import TermState

        mine = {k: v for k, v in vars(TermState).items() if k.isupper()}
        assert mine == self.SERVER_TERM_STATE

    def test_term_conflict_codes_match_server(self):
        from intelion_cloud import TermConflictCode

        mine = {k: v for k, v in vars(TermConflictCode).items() if k.isupper()}
        assert mine == self.SERVER_TERM_CODES

    def test_unreachable_plan_withdrawn_code_is_not_listed(self):
        from intelion_cloud import TermConflictCode

        assert not hasattr(TermConflictCode, "AUTO_RENEWAL_PLAN_WITHDRAWN")

    def test_no_snapshot_state_is_read_from_server(self):
        server = CloudServer.from_dict({**SAMPLE_CLOUD_SERVER, "term_state": "no_snapshot"})
        assert server.term_state == "no_snapshot"


class TestErrorCodeCarriesDiskCodes:
    @respx.mock(base_url=API_URL)
    def test_migrate_disk_refusal_code(self, respx_mock):
        from intelion_cloud import ConflictError

        respx_mock.post("cloud-servers/42/migrate/").respond(
            409, json={"error_code": "not_draft", "detail": "running"}
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(ConflictError) as info:
            client.cloud_servers.migrate(42, flavor_id=1, price_plan=0, ssd_count=256)
        client.close()
        assert info.value.error_code == "not_draft"

    @respx.mock(base_url=API_URL)
    def test_feature_disabled_is_not_found(self, respx_mock):
        from intelion_cloud import NotFoundError

        respx_mock.post("cloud-servers/42/migrate/").respond(
            404, json={"error_code": "feature_disabled", "detail": "off"}
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(NotFoundError) as info:
            client.cloud_servers.migrate(42, flavor_id=1, price_plan=0, ssd_count=256)
        client.close()
        assert info.value.error_code == "feature_disabled"

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
