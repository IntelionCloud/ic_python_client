"""Tests for user resource."""

import respx

from intelion_cloud import IntelionCloud

from .conftest import API_URL, BASE_URL, SAMPLE_USER


class TestUsers:
    @respx.mock(base_url=API_URL)
    def test_me(self, respx_mock):
        respx_mock.get("users/").respond(
            200,
            json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [SAMPLE_USER],
            },
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        user = client.users.me()
        assert user.id == 7
        assert user.email == "test@example.com"
        assert user.current_balance_rub_cents == 5000000
        client.close()

    @respx.mock(base_url=API_URL)
    def test_get(self, respx_mock):
        respx_mock.get("users/7/").respond(200, json=SAMPLE_USER)
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        user = client.users.get(7)
        assert user.id == 7
        assert user.username == "testuser"
        client.close()

    @respx.mock(base_url=API_URL)
    def test_update(self, respx_mock):
        updated = {**SAMPLE_USER, "first_name": "Updated"}
        respx_mock.patch("users/7/").respond(200, json=updated)
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        user = client.users.update(7, first_name="Updated")
        assert user.first_name == "Updated"
        import json

        body = json.loads(respx_mock.calls[0].request.content)
        assert body == {"first_name": "Updated"}
        client.close()
