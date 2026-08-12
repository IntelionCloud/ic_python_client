"""SSH key resource — list, add and remove account SSH public keys.

The endpoint returns a **plain JSON array**, not a DRF paginated envelope,
so there is no ``page`` argument here — unlike every other list in this SDK.
Rate limit is 30 requests/minute per user; exceeding it raises
:class:`~intelion_cloud.exceptions.RateLimitError`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..models.ssh_keys import SSHKey
from ._base import AsyncResource, SyncResource

_PATH = "ssh-keys/"


def _create_payload(public_key: str, name: Optional[str]) -> Dict[str, Any]:
    """Build the POST body.

    ``name`` is optional: the server falls back to the trailing comment of the
    key (``ssh-<type> <base64> <comment>``) and rejects the request only when
    both are missing.
    """
    payload: Dict[str, Any] = {"public_key": public_key}
    if name is not None:
        payload["name"] = name
    return payload


class SSHKeys(SyncResource):
    """Synchronous SSH key operations."""

    def list(self) -> List[SSHKey]:
        """List the account's SSH keys, newest first."""
        data = self._get(_PATH)
        return [SSHKey.from_dict(item) for item in data]

    def create(self, public_key: str, *, name: Optional[str] = None) -> SSHKey:
        """Add an SSH public key.

        Raises :class:`ValidationError` (400) if the key is malformed, of an
        unsupported type, or an RSA key shorter than 2048 bits;
        :class:`ConflictError` (409) if the same fingerprint is already on the
        account.
        """
        return SSHKey.from_dict(self._post(_PATH, json=_create_payload(public_key, name)))

    def delete(self, key_id: int) -> None:
        """Remove a key. Raises :class:`NotFoundError` if it is not yours."""
        self._delete(f"{_PATH}{key_id}/")


class AsyncSSHKeys(AsyncResource):
    """Asynchronous SSH key operations."""

    async def list(self) -> List[SSHKey]:
        data = await self._get(_PATH)
        return [SSHKey.from_dict(item) for item in data]

    async def create(self, public_key: str, *, name: Optional[str] = None) -> SSHKey:
        data = await self._post(_PATH, json=_create_payload(public_key, name))
        return SSHKey.from_dict(data)

    async def delete(self, key_id: int) -> None:
        await self._delete(f"{_PATH}{key_id}/")
