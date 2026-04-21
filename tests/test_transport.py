"""Tests for transport layer: retry logic, error handling, rate limiting."""

import httpx
import pytest
import respx

from intelion_cloud import IntelionCloud
from intelion_cloud.exceptions import (
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)

from .conftest import API_URL, BASE_URL


class TestErrorMapping:
    """Test HTTP status codes are mapped to correct exception types."""

    @respx.mock(base_url=API_URL)
    def test_401_raises_authentication_error(self, respx_mock):
        respx_mock.get("flavors/").respond(401, json={"detail": "Invalid token."})
        client = IntelionCloud(token="bad", base_url=BASE_URL)
        with pytest.raises(AuthenticationError) as exc_info:
            client.flavors.list()
        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value)
        client.close()

    @respx.mock(base_url=API_URL)
    def test_403_raises_forbidden_error(self, respx_mock):
        respx_mock.get("cloud-servers/1/").respond(403, json={"detail": "Forbidden"})
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(ForbiddenError):
            client.cloud_servers.get(1)
        client.close()

    @respx.mock(base_url=API_URL)
    def test_404_raises_not_found_error(self, respx_mock):
        respx_mock.get("cloud-servers/999/").respond(404, json={"detail": "Not found."})
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(NotFoundError):
            client.cloud_servers.get(999)
        client.close()

    @respx.mock(base_url=API_URL)
    def test_409_raises_conflict_error(self, respx_mock):
        respx_mock.post("cloud-servers/1/actions/").respond(
            409, json={"detail": "Server busy"}
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(ConflictError):
            client.cloud_servers.start(1)
        client.close()

    @respx.mock(base_url=API_URL)
    def test_400_raises_validation_error_with_field_errors(self, respx_mock):
        errors = {"name": ["This field is required."], "flavor_id": ["Invalid flavor."]}
        respx_mock.post("cloud-servers/").respond(400, json=errors)
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(ValidationError) as exc_info:
            client.cloud_servers.create(
                name="",
                flavor_id=999,
                ssd_count=30,
                os_id=1,
            )
        assert exc_info.value.field_errors["name"] == ["This field is required."]
        client.close()


class TestRetryLogic:
    """Test retry behavior for rate limits and server errors."""

    @respx.mock(base_url=API_URL)
    def test_429_retries_and_succeeds(self, respx_mock):
        route = respx_mock.get("flavors/")
        # First call returns 429, second succeeds
        route.side_effect = [
            httpx.Response(429, json={"detail": "Rate limited"}),
            httpx.Response(200, json={"count": 0, "next": None, "previous": None, "results": []}),
        ]
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        result = client.flavors.list()
        assert result == []
        assert route.call_count == 2
        client.close()

    @respx.mock(base_url=API_URL)
    def test_429_exhausts_retries(self, respx_mock):
        route = respx_mock.get("flavors/")
        # All calls return 429
        route.side_effect = [
            httpx.Response(429, json={"detail": "Rate limited"}),
            httpx.Response(429, json={"detail": "Rate limited"}),
            httpx.Response(429, json={"detail": "Rate limited"}),
            httpx.Response(429, json={"detail": "Rate limited"}),
        ]
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(RateLimitError):
            client.flavors.list()
        # 1 initial + 3 retries = 4 calls
        assert route.call_count == 4
        client.close()

    @respx.mock(base_url=API_URL)
    def test_500_retries_on_get(self, respx_mock):
        route = respx_mock.get("cloud-servers/1/")
        route.side_effect = [
            httpx.Response(500, json={"detail": "Internal error"}),
            httpx.Response(
                200,
                json={
                    "id": 1,
                    "name": "test",
                    "status": 2,
                    "price_plan": 0,
                    "is_auto_renewal": False,
                    "monthly_price_rub_cents": 0,
                    "hourly_price_rub_cents": 0,
                    "server_full_rent_price_rub_cents": 0,
                },
            ),
        ]
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        server = client.cloud_servers.get(1)
        assert server.id == 1
        assert route.call_count == 2
        client.close()

    @respx.mock(base_url=API_URL)
    def test_500_no_retry_on_post(self, respx_mock):
        """POST requests should not retry on 5xx (not idempotent)."""
        route = respx_mock.post("cloud-servers/")
        route.side_effect = [
            httpx.Response(500, json={"detail": "Internal error"}),
        ]
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(ServerError):
            client.cloud_servers.create(
                name="test",
                flavor_id=1,
                ssd_count=30,
                os_id=1,
            )
        assert route.call_count == 1
        client.close()

    @respx.mock(base_url=API_URL)
    def test_429_retries_on_post(self, respx_mock):
        """POST requests SHOULD retry on 429 (rate limit)."""
        route = respx_mock.post("cloud-servers/")
        route.side_effect = [
            httpx.Response(429, json={"detail": "Rate limited"}),
            httpx.Response(
                201,
                json={
                    "id": 1,
                    "name": "test",
                    "status": -2,
                    "price_plan": 0,
                    "is_auto_renewal": False,
                    "monthly_price_rub_cents": 0,
                    "hourly_price_rub_cents": 0,
                    "server_full_rent_price_rub_cents": 0,
                },
            ),
        ]
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        server = client.cloud_servers.create(
            name="test",
            flavor_id=1,
            ssd_count=30,
            os_id=1,
        )
        assert server.id == 1
        assert route.call_count == 2
        client.close()
