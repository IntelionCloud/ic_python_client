"""Tests for cloud server resource methods."""

import httpx
import pytest
import respx

from intelion_cloud import ConflictError, IntelionCloud, ServerState, TermState, ValidationError
from intelion_cloud._pagination import PaginatedResponse

from .conftest import (
    API_URL,
    BASE_URL,
    SAMPLE_CLOUD_SERVER,
    SAMPLE_COLD_SERVER,
    SAMPLE_TERM_SERVER,
    SAMPLE_TERM_USAGE_ACT,
)


class TestCloudServersList:
    @respx.mock(base_url=API_URL)
    def test_list_all(self, respx_mock):
        respx_mock.get("cloud-servers/").respond(
            200,
            json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [SAMPLE_CLOUD_SERVER],
            },
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        servers = client.cloud_servers.list()
        assert len(servers) == 1
        assert servers[0].id == 42
        assert servers[0].name == "my-gpu-server"
        client.close()

    @respx.mock(base_url=API_URL)
    def test_list_paginated(self, respx_mock):
        respx_mock.get("cloud-servers/", params={"page": 1}).respond(
            200,
            json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [SAMPLE_CLOUD_SERVER],
            },
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        page = client.cloud_servers.list(page=1)
        assert isinstance(page, PaginatedResponse)
        assert page.count == 1
        assert len(page.results) == 1
        assert not page.has_next
        client.close()

    @respx.mock(base_url=API_URL)
    def test_list_auto_pagination(self, respx_mock):
        """Auto-pagination follows next URLs."""
        respx_mock.get("cloud-servers/").mock(
            side_effect=[
                httpx.Response(
                    200,
                    json={
                        "count": 2,
                        "next": f"{API_URL}cloud-servers/?page=2",
                        "previous": None,
                        "results": [{**SAMPLE_CLOUD_SERVER, "id": 1, "name": "server-1"}],
                    },
                ),
                httpx.Response(
                    200,
                    json={
                        "count": 2,
                        "next": None,
                        "previous": f"{API_URL}cloud-servers/",
                        "results": [{**SAMPLE_CLOUD_SERVER, "id": 2, "name": "server-2"}],
                    },
                ),
            ]
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        servers = client.cloud_servers.list()
        assert len(servers) == 2
        assert servers[0].id == 1
        assert servers[1].id == 2
        client.close()


class TestCloudServersGet:
    @respx.mock(base_url=API_URL)
    def test_get(self, respx_mock):
        respx_mock.get("cloud-servers/42/").respond(200, json=SAMPLE_CLOUD_SERVER)
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        server = client.cloud_servers.get(42)
        assert server.id == 42
        assert server.gpu is not None
        assert server.gpu.name == "NVIDIA H100"
        client.close()

    @respx.mock(base_url=API_URL)
    def test_get_server_on_confirmed_term(self, respx_mock):
        """GET of a server bound by a 12-month term: the SDK exposes the whole term block."""
        respx_mock.get("cloud-servers/42/").respond(200, json=SAMPLE_TERM_SERVER)
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        server = client.cloud_servers.get(42)
        assert server.term_state == TermState.ACTIVE
        assert server.term_months == 12
        assert server.term_discount_percent == 35
        assert server.term_ends_at == "2027-09-01T05:00:00+03:00"
        assert server.is_bound_by_term is True
        assert server.is_renewal_mandatory is True
        assert server.billing_cycle_months == 1
        client.close()

    @respx.mock(base_url=API_URL)
    def test_get_server_in_cold_storage(self, respx_mock):
        """GET of a cold server: storage block, resume price and no fake running act."""
        respx_mock.get("cloud-servers/42/").respond(200, json=SAMPLE_COLD_SERVER)
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        server = client.cloud_servers.get(42)
        assert server.server_state == ServerState.COLD_STORAGE
        assert server.cold_storage is not None
        assert server.cold_storage.storage_gb == "50.000"
        assert server.cold_storage.accrued_debt_rub_cents == 2333
        assert server.resume_usage_act is not None
        assert server.resume_usage_act.next_payment.amount_rub_cents == 16071
        assert server.usage_act is None
        assert server.cold_free is None
        client.close()

    @respx.mock(base_url=API_URL)
    def test_get_server_usage_act_cost_fields(self, respx_mock):
        """The act inside a server response carries the cost / discount / promocode fields."""
        respx_mock.get("cloud-servers/42/").respond(
            200, json={**SAMPLE_TERM_SERVER, "usage_act": SAMPLE_TERM_USAGE_ACT}
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        server = client.cloud_servers.get(42)
        act = server.usage_act
        assert act.full_planned_cost_rub_cents == 6318000
        assert act.next_charge_rub_cents == 6318000
        assert act.discount_percent == server.term_discount_percent == 35
        assert act.promocode_code == "WELCOME10"
        assert act.promocode_discount_value == 10
        client.close()


class TestCloudServersCreate:
    @respx.mock(base_url=API_URL)
    def test_create(self, respx_mock):
        respx_mock.post("cloud-servers/").respond(
            201, json={**SAMPLE_CLOUD_SERVER, "status": -2}
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        server = client.cloud_servers.create(
            name="my-gpu-server",
            flavor_id=1,
            ssd_count=128,
            os_id=1,
            price_plan=0,
            addon_ids=[7],
        )
        assert server.id == 42
        # Verify the request payload
        req = respx_mock.calls[0].request
        import json

        body = json.loads(req.content)
        assert body["name"] == "my-gpu-server"
        assert body["flavor_id"] == 1
        assert body["ssd_count"] == 128
        assert body["os_id"] == 1
        assert body["price_plan"] == 0
        assert body["addon_ids"] == [7]
        assert "cpu_id" not in body
        assert "gpu_id" not in body
        assert "ram_id" not in body
        client.close()


class TestCloudServersUpdate:
    @respx.mock(base_url=API_URL)
    def test_update_name(self, respx_mock):
        respx_mock.patch("cloud-servers/42/").respond(
            200, json={**SAMPLE_CLOUD_SERVER, "name": "new-name"}
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        server = client.cloud_servers.update(42, name="new-name")
        assert server.name == "new-name"
        client.close()

    @respx.mock(base_url=API_URL)
    def test_update_auto_renewal_off_outside_term(self, respx_mock):
        """Hourly server: switching auto-renewal off is an ordinary PATCH."""
        respx_mock.patch("cloud-servers/42/").respond(
            200, json={**SAMPLE_CLOUD_SERVER, "is_auto_renewal": False}
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        server = client.cloud_servers.update(42, is_auto_renewal=False)
        assert server.is_auto_renewal is False
        assert server.is_bound_by_term is False
        client.close()

    @respx.mock(base_url=API_URL)
    def test_update_auto_renewal_off_under_term_is_rejected(self, respx_mock):
        """Server bound by a confirmed term answers 400 to ``is_auto_renewal=false``.

        ``UserConfigurationSerializer.validate_is_auto_renewal`` on the server:
        auto-renewal cannot be switched off before the term ends, the rental is
        ended through the termination flow instead. The SDK surfaces it as
        ``ValidationError`` with the field error, nothing is swallowed.
        """
        respx_mock.patch("cloud-servers/42/").respond(
            400,
            json={
                "is_auto_renewal": [
                    "Автопродление нельзя выключить до конца срока аренды: "
                    "аренда прекращается через «прекратить аренду»."
                ]
            },
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(ValidationError) as exc_info:
            client.cloud_servers.update(42, is_auto_renewal=False)
        assert exc_info.value.status_code == 400
        assert "is_auto_renewal" in exc_info.value.field_errors
        assert respx_mock.calls.call_count == 1
        client.close()


class TestCloudServersActions:
    @respx.mock(base_url=API_URL)
    def test_start(self, respx_mock):
        respx_mock.post("cloud-servers/42/actions/").respond(
            200, json={**SAMPLE_CLOUD_SERVER, "status": 2}
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        server = client.cloud_servers.start(42)
        assert server.status == 2
        import json

        body = json.loads(respx_mock.calls[0].request.content)
        assert body["status"] == 2
        client.close()

    @respx.mock(base_url=API_URL)
    def test_stop(self, respx_mock):
        respx_mock.post("cloud-servers/42/actions/").respond(
            200, json={**SAMPLE_CLOUD_SERVER, "status": -1}
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        server = client.cloud_servers.stop(42)
        assert server.status == -1
        import json

        body = json.loads(respx_mock.calls[0].request.content)
        assert body["status"] == -1
        client.close()

    @respx.mock(base_url=API_URL)
    def test_reboot(self, respx_mock):
        respx_mock.post("cloud-servers/42/actions/").respond(
            200, json=SAMPLE_CLOUD_SERVER
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        server = client.cloud_servers.reboot(42)
        import json

        body = json.loads(respx_mock.calls[0].request.content)
        assert body["status"] == "REBOOT"
        client.close()

    @respx.mock(base_url=API_URL)
    def test_delete(self, respx_mock):
        respx_mock.post("cloud-servers/42/actions/").respond(
            200, json={**SAMPLE_CLOUD_SERVER, "status": -3}
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        server = client.cloud_servers.delete(42)
        assert server.status == -3
        client.close()

    @respx.mock(base_url=API_URL)
    def test_reinstall_os(self, respx_mock):
        respx_mock.post("cloud-servers/42/reinstall-os/").respond(
            200, json=SAMPLE_CLOUD_SERVER
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        server = client.cloud_servers.reinstall_os(42)
        assert server.id == SAMPLE_CLOUD_SERVER["id"]
        client.close()

    @pytest.mark.parametrize(
        "code",
        ["TERM_CONDITIONS_REQUIRED", "TERM_RENEWAL_IN_PROGRESS", "LEGACY_TERMS_CONSENT_REQUIRED"],
    )
    @respx.mock(base_url=API_URL)
    def test_reinstall_os_term_refusal_carries_error_code(self, respx_mock, code):
        """Without an open period reinstall_os is a start: the 409 carries the term code."""
        respx_mock.post("cloud-servers/42/reinstall-os/").respond(
            409, json={"error_code": code, "message": "refused", "detail": "refused"}
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(ConflictError) as excinfo:
            client.cloud_servers.reinstall_os(42)
        assert excinfo.value.error_code == code
        client.close()

    @respx.mock(base_url=API_URL)
    def test_start_with_auto_renewal(self, respx_mock):
        respx_mock.post("cloud-servers/42/actions/").respond(
            200, json=SAMPLE_CLOUD_SERVER
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        client.cloud_servers.start(42, is_auto_renewal=True, run_on_affordable_time=True)
        import json

        body = json.loads(respx_mock.calls[0].request.content)
        assert body["isAutoRenewal"] is True
        assert body["run_on_affordable_time"] is True
        client.close()


class TestCloudServersInfo:
    @respx.mock(base_url=API_URL)
    def test_get_status(self, respx_mock):
        respx_mock.get("cloud-servers/42/status/").respond(
            200,
            json={"can_start": True, "affordable_runtime_seconds": 7200},
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        status = client.cloud_servers.get_status(42)
        assert status.can_start is True
        assert status.affordable_runtime_seconds == 7200
        client.close()

    @respx.mock(base_url=API_URL)
    def test_get_password(self, respx_mock):
        respx_mock.get("cloud-servers/42/password/").respond(
            200, json={"password": "s3cret!"}
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        password = client.cloud_servers.get_password(42)
        assert password == "s3cret!"
        client.close()


class TestCloudServersAdvanced:
    @respx.mock(base_url=API_URL)
    def test_clone(self, respx_mock):
        clone_data = {**SAMPLE_CLOUD_SERVER, "id": 43, "name": "my-gpu-server-clone"}
        respx_mock.post("cloud-servers/42/clone/").respond(200, json=clone_data)
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        clone = client.cloud_servers.clone(42)
        assert clone.id == 43
        client.close()

    @respx.mock(base_url=API_URL)
    def test_migrate(self, respx_mock):
        respx_mock.post("cloud-servers/42/migrate/").respond(
            200, json={**SAMPLE_CLOUD_SERVER, "flavor_oid": "new-flavor-uuid"}
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        server = client.cloud_servers.migrate(
            42,
            flavor_id=5,
            price_plan=1,
        )
        assert server.flavor_oid == "new-flavor-uuid"
        import json

        body = json.loads(respx_mock.calls[0].request.content)
        assert body == {"flavor_id": 5, "price_plan": 1}
        client.close()
