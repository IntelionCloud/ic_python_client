"""Tests for cloud server resource methods."""

import httpx
import pytest
import respx

from intelion_cloud import IntelionCloud
from intelion_cloud._pagination import PaginatedResponse

from .conftest import API_URL, BASE_URL, SAMPLE_CLOUD_SERVER


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
            ssd_count=50,
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
        assert body["ssd_count"] == 50
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
