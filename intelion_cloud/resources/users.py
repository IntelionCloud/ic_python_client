"""User resource — current user info and profile update."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..models.users import User
from ._base import AsyncResource, SyncResource

_PATH = "users/"


class Users(SyncResource):
    """Synchronous user operations."""

    def me(self) -> User:
        """Get the current authenticated user's profile.

        The API requires user ID in the URL. We first list users (returns only
        the current user) then fetch by ID.
        """
        data = self._get(_PATH)
        # The users endpoint returns a paginated list with only the current user
        results = data.get("results", [data]) if isinstance(data, dict) else data
        if not results:
            raise ValueError("No user returned by the API")
        user_data = results[0]
        return User.from_dict(user_data)

    def get(self, user_id: int) -> User:
        """Get a user by ID (typically your own)."""
        data = self._get(f"{_PATH}{user_id}/")
        return User.from_dict(data)

    def update(
        self,
        user_id: int,
        *,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        company_name: Optional[str] = None,
        last_viewed_event: Optional[str] = None,
        default_payment_type: Optional[str] = None,
    ) -> User:
        """Update user profile fields."""
        payload: Dict[str, Any] = {}
        if first_name is not None:
            payload["first_name"] = first_name
        if last_name is not None:
            payload["last_name"] = last_name
        if company_name is not None:
            payload["company_name"] = company_name
        if last_viewed_event is not None:
            payload["last_viewed_event"] = last_viewed_event
        if default_payment_type is not None:
            payload["default_payment_type"] = default_payment_type

        data = self._patch(f"{_PATH}{user_id}/", json=payload)
        return User.from_dict(data)


class AsyncUsers(AsyncResource):
    """Asynchronous user operations."""

    async def me(self) -> User:
        data = await self._get(_PATH)
        results = data.get("results", [data]) if isinstance(data, dict) else data
        if not results:
            raise ValueError("No user returned by the API")
        user_data = results[0]
        return User.from_dict(user_data)

    async def get(self, user_id: int) -> User:
        data = await self._get(f"{_PATH}{user_id}/")
        return User.from_dict(data)

    async def update(
        self,
        user_id: int,
        *,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        company_name: Optional[str] = None,
        last_viewed_event: Optional[str] = None,
        default_payment_type: Optional[str] = None,
    ) -> User:
        payload: Dict[str, Any] = {}
        if first_name is not None:
            payload["first_name"] = first_name
        if last_name is not None:
            payload["last_name"] = last_name
        if company_name is not None:
            payload["company_name"] = company_name
        if last_viewed_event is not None:
            payload["last_viewed_event"] = last_viewed_event
        if default_payment_type is not None:
            payload["default_payment_type"] = default_payment_type

        data = await self._patch(f"{_PATH}{user_id}/", json=payload)
        return User.from_dict(data)
