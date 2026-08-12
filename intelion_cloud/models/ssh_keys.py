"""SSH public key model (UserSSHKey on the server side)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ._base import _get


@dataclass(frozen=True)
class SSHKey:
    """A public SSH key registered on the account.

    The API returns the key material in full, not just the fingerprint — a
    public key is public by definition and the endpoint only ever serves
    ``request.user.ssh_keys``.
    """

    id: int
    name: str
    public_key: str
    key_type: str
    """``ssh-ed25519``, ``ssh-rsa`` or ``ecdsa-sha2-nistp{256,384,521}``."""
    fingerprint_sha256: str
    """``SHA256:<base64>`` — same shape as ``ssh-keygen -lf``."""
    created_at: Optional[str] = None
    last_used_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SSHKey:
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            public_key=data.get("public_key", ""),
            key_type=data.get("key_type", ""),
            fingerprint_sha256=data.get("fingerprint_sha256", ""),
            created_at=_get(data, "created_at"),
            last_used_at=_get(data, "last_used_at"),
        )
