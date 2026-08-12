"""SSH key resource.

Server side: ``website/user_panel/views/ssh_keys_api_view.py``. Note it is a
plain ``APIView``, not a ViewSet — GET returns a **bare JSON array**, not the
DRF ``{count, next, previous, results}`` envelope every other list uses.
"""

import httpx
import pytest
import respx

from intelion_cloud import IntelionCloud, SSHKey
from intelion_cloud.exceptions import ConflictError, NotFoundError, ValidationError

from .conftest import API_URL, BASE_URL

KEY = (
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFS9eO4Ptn+HiV8OuZYtcR93nvaZVebxFXkwHKXnp1dq "
    "max@macbook"
)
SAMPLE_KEY = {
    "id": 12,
    "name": "max@macbook",
    "public_key": KEY,
    "key_type": "ssh-ed25519",
    "fingerprint_sha256": "SHA256:abc123",
    "created_at": "2026-08-12T10:00:00+00:00",
    "last_used_at": None,
}


class TestSSHKeyModel:
    def test_from_dict(self):
        key = SSHKey.from_dict(SAMPLE_KEY)
        assert key.id == 12
        assert key.key_type == "ssh-ed25519"
        assert key.fingerprint_sha256 == "SHA256:abc123"
        assert key.last_used_at is None


class TestSSHKeys:
    @respx.mock(base_url=API_URL)
    def test_list_parses_bare_array(self, respx_mock):
        """Ответ — голый массив; обёртки {count,results} тут нет."""
        respx_mock.get("ssh-keys/").respond(200, json=[SAMPLE_KEY])
        client = IntelionCloud(token="tok", base_url=BASE_URL)

        keys = client.ssh_keys.list()

        assert len(keys) == 1
        assert keys[0].name == "max@macbook"

    @respx.mock(base_url=API_URL)
    def test_list_empty(self, respx_mock):
        respx_mock.get("ssh-keys/").respond(200, json=[])
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        assert client.ssh_keys.list() == []

    @respx.mock(base_url=API_URL)
    def test_create_sends_name_when_given(self, respx_mock):
        route = respx_mock.post("ssh-keys/").respond(201, json=SAMPLE_KEY)
        client = IntelionCloud(token="tok", base_url=BASE_URL)

        key = client.ssh_keys.create(KEY, name="max@macbook")

        assert key.id == 12
        import json as _json

        assert _json.loads(route.calls[0].request.content) == {
            "public_key": KEY,
            "name": "max@macbook",
        }

    @respx.mock(base_url=API_URL)
    def test_create_omits_name_when_not_given(self, respx_mock):
        """Без name сервер берёт комментарий из хвоста ключа — не шлём пустую строку."""
        route = respx_mock.post("ssh-keys/").respond(201, json=SAMPLE_KEY)
        client = IntelionCloud(token="tok", base_url=BASE_URL)

        client.ssh_keys.create(KEY)

        import json as _json

        assert _json.loads(route.calls[0].request.content) == {"public_key": KEY}

    @respx.mock(base_url=API_URL)
    def test_create_duplicate_raises_conflict(self, respx_mock):
        respx_mock.post("ssh-keys/").respond(409, json={"error": "Этот ключ уже добавлен"})
        client = IntelionCloud(token="tok", base_url=BASE_URL)

        with pytest.raises(ConflictError):
            client.ssh_keys.create(KEY)

    @respx.mock(base_url=API_URL)
    def test_create_invalid_key_raises_validation(self, respx_mock):
        respx_mock.post("ssh-keys/").respond(400, json={"error": "Ключ невалиден"})
        client = IntelionCloud(token="tok", base_url=BASE_URL)

        with pytest.raises(ValidationError):
            client.ssh_keys.create("not-a-key")

    @respx.mock(base_url=API_URL)
    def test_delete_returns_none_on_204(self, respx_mock):
        route = respx_mock.delete("ssh-keys/12/").respond(204)
        client = IntelionCloud(token="tok", base_url=BASE_URL)

        assert client.ssh_keys.delete(12) is None
        assert route.calls[0].request.method == "DELETE"

    @respx.mock(base_url=API_URL)
    def test_delete_foreign_key_raises_not_found(self, respx_mock):
        respx_mock.delete("ssh-keys/999/").respond(404)
        client = IntelionCloud(token="tok", base_url=BASE_URL)

        with pytest.raises(NotFoundError):
            client.ssh_keys.delete(999)
