"""Tests for client initialization and auth headers."""

import httpx
import pytest
import respx

from intelion_cloud import IntelionCloud, AsyncIntelionCloud
from intelion_cloud.constants import DEFAULT_BASE_URL

from .conftest import BASE_URL, API_URL


class TestSyncClientInit:
    def test_default_base_url(self):
        client = IntelionCloud(token="tok")
        assert client._transport._client.base_url == httpx.URL(f"{DEFAULT_BASE_URL}/api/v2/")
        client.close()

    def test_custom_base_url(self):
        client = IntelionCloud(token="tok", base_url="https://custom.host")
        assert client._transport._client.base_url == httpx.URL("https://custom.host/api/v2/")
        client.close()

    def test_auth_header_set(self):
        client = IntelionCloud(token="my-secret-token")
        headers = client._transport._client.headers
        assert headers["authorization"] == "Token my-secret-token"
        assert headers["accept"] == "application/json"
        client.close()

    def test_context_manager(self):
        with IntelionCloud(token="tok", base_url=BASE_URL) as client:
            assert client.cloud_servers is not None
            assert client.flavors is not None
            assert client.os_images is not None
            assert client.users is not None

    def test_resources_attached(self):
        client = IntelionCloud(token="tok")
        assert hasattr(client, "cloud_servers")
        assert hasattr(client, "flavors")
        assert hasattr(client, "os_images")
        assert hasattr(client, "users")
        client.close()


class TestAsyncClientInit:
    def test_auth_header_set(self):
        client = AsyncIntelionCloud(token="async-token")
        headers = client._transport._client.headers
        assert headers["authorization"] == "Token async-token"

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        async with AsyncIntelionCloud(token="tok", base_url=BASE_URL) as client:
            assert client.cloud_servers is not None
            assert client.flavors is not None
