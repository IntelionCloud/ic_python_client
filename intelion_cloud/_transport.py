"""HTTP transport layer with retry logic, error mapping, and logging."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import httpx

from .constants import DEFAULT_BASE_URL, DEFAULT_CONNECT_TIMEOUT, DEFAULT_TIMEOUT
from .exceptions import (
    APIError,
    AuthenticationError,
    ConnectionError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    PaymentRequiredError,
    RateLimitError,
    ServerError,
    ValidationError,
)

logger = logging.getLogger("intelion_cloud")

_IDEMPOTENT_METHODS = frozenset({"GET", "PUT", "PATCH", "DELETE"})

# Retry configuration
_MAX_RATE_LIMIT_RETRIES = 3
_MAX_SERVER_ERROR_RETRIES = 1
_MAX_CONNECTION_RETRIES = 2
_RATE_LIMIT_BASE_DELAY = 1.0
_SERVER_ERROR_DELAY = 1.0
_CONNECTION_BASE_DELAY = 0.5


def _build_api_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/api/v2/"


def _raise_for_status(response: httpx.Response) -> None:
    """Map HTTP error responses to typed exceptions."""
    status = response.status_code
    if status < 400:
        return

    try:
        body = response.json()
    except Exception:
        body = response.text

    message = _extract_message(body, status)

    if status == 400:
        field_errors = body if isinstance(body, dict) else {}
        raise ValidationError(
            message,
            status_code=status,
            response_body=body,
            field_errors=field_errors,
        )
    if status == 401:
        raise AuthenticationError(message, status_code=status, response_body=body)
    if status == 402:
        # AI API self-serve gate (inference_api_keys.request_access) — body
        # carries shortfall_rub_cents. A dedicated type so callers don't have
        # to string-match a generic APIError to show "top up N ₽".
        raise PaymentRequiredError(message, status_code=status, response_body=body)
    if status == 403:
        raise ForbiddenError(message, status_code=status, response_body=body)
    if status == 404:
        raise NotFoundError(message, status_code=status, response_body=body)
    if status == 409:
        raise ConflictError(message, status_code=status, response_body=body)
    if status == 429:
        retry_after = _parse_retry_after(response)
        raise RateLimitError(
            message,
            status_code=status,
            response_body=body,
            retry_after=retry_after,
        )
    if status >= 500:
        raise ServerError(message, status_code=status, response_body=body)

    raise APIError(message, status_code=status, response_body=body)


def _extract_message(body: Any, status_code: int) -> str:
    if isinstance(body, dict):
        for key in ("detail", "message", "error", "non_field_errors"):
            if key in body:
                val = body[key]
                if isinstance(val, list):
                    return "; ".join(str(v) for v in val)
                return str(val)
    if isinstance(body, str) and body:
        return body
    return f"API error {status_code}"


def _parse_retry_after(response: httpx.Response) -> Optional[float]:
    header = response.headers.get("retry-after")
    if header is None:
        return None
    try:
        return float(header)
    except (ValueError, TypeError):
        return None


def _should_retry_rate_limit(attempt: int) -> bool:
    return attempt < _MAX_RATE_LIMIT_RETRIES


def _should_retry_server_error(method: str, attempt: int) -> bool:
    return attempt < _MAX_SERVER_ERROR_RETRIES and method in _IDEMPOTENT_METHODS


def _should_retry_connection(method: str, attempt: int) -> bool:
    return attempt < _MAX_CONNECTION_RETRIES and method in _IDEMPOTENT_METHODS


def _rate_limit_delay(attempt: int, retry_after: Optional[float]) -> float:
    if retry_after is not None and retry_after > 0:
        return min(retry_after, 30.0)
    return _RATE_LIMIT_BASE_DELAY * (2**attempt)


class SyncTransport:
    """Synchronous HTTP transport using httpx.Client."""

    def __init__(
        self,
        token: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
    ) -> None:
        self._client = httpx.Client(
            base_url=_build_api_url(base_url),
            headers={
                "Authorization": f"Token {token}",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(timeout, connect=connect_timeout),
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """``headers`` are merged on top of the client-level defaults (httpx
        behaviour) — used for ``Accept: text/csv`` on
        ``inference_api_keys.usage_range_csv()``, whose response the
        client-wide ``Accept: application/json`` would otherwise 406 on."""
        attempt = 0
        while True:
            start = time.monotonic()
            try:
                response = self._client.request(
                    method,
                    path,
                    json=json,
                    params=params,
                    headers=headers,
                )
                duration = time.monotonic() - start
                logger.debug(
                    "%s %s -> %d (%.2fs)",
                    method,
                    path,
                    response.status_code,
                    duration,
                )

                try:
                    _raise_for_status(response)
                except RateLimitError as exc:
                    if _should_retry_rate_limit(attempt):
                        delay = _rate_limit_delay(attempt, exc.retry_after)
                        logger.warning(
                            "Rate limited, retry %d/%d in %.1fs",
                            attempt + 1,
                            _MAX_RATE_LIMIT_RETRIES,
                            delay,
                        )
                        time.sleep(delay)
                        attempt += 1
                        continue
                    raise
                except ServerError:
                    if _should_retry_server_error(method, attempt):
                        logger.warning(
                            "Server error %d, retry %d/%d in %.1fs",
                            response.status_code,
                            attempt + 1,
                            _MAX_SERVER_ERROR_RETRIES,
                            _SERVER_ERROR_DELAY,
                        )
                        time.sleep(_SERVER_ERROR_DELAY)
                        attempt += 1
                        continue
                    raise

                return response

            except (httpx.ConnectError, httpx.ReadError, httpx.WriteError) as exc:
                if _should_retry_connection(method, attempt):
                    delay = _CONNECTION_BASE_DELAY * (2**attempt)
                    logger.warning(
                        "Connection error (%s), retry %d/%d in %.1fs",
                        type(exc).__name__,
                        attempt + 1,
                        _MAX_CONNECTION_RETRIES,
                        delay,
                    )
                    time.sleep(delay)
                    attempt += 1
                    continue
                raise ConnectionError(str(exc)) from exc
            except httpx.TimeoutException as exc:
                if method == "GET" and attempt < _MAX_CONNECTION_RETRIES:
                    delay = _RATE_LIMIT_BASE_DELAY * (2**attempt)
                    logger.warning(
                        "Timeout on GET, retry %d/%d in %.1fs",
                        attempt + 1,
                        _MAX_CONNECTION_RETRIES,
                        delay,
                    )
                    time.sleep(delay)
                    attempt += 1
                    continue
                raise ConnectionError(str(exc)) from exc

    def close(self) -> None:
        self._client.close()


class AsyncTransport:
    """Asynchronous HTTP transport using httpx.AsyncClient."""

    def __init__(
        self,
        token: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=_build_api_url(base_url),
            headers={
                "Authorization": f"Token {token}",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(timeout, connect=connect_timeout),
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        import asyncio

        attempt = 0
        while True:
            start = time.monotonic()
            try:
                response = await self._client.request(
                    method,
                    path,
                    json=json,
                    params=params,
                    headers=headers,
                )
                duration = time.monotonic() - start
                logger.debug(
                    "%s %s -> %d (%.2fs)",
                    method,
                    path,
                    response.status_code,
                    duration,
                )

                try:
                    _raise_for_status(response)
                except RateLimitError as exc:
                    if _should_retry_rate_limit(attempt):
                        delay = _rate_limit_delay(attempt, exc.retry_after)
                        logger.warning(
                            "Rate limited, retry %d/%d in %.1fs",
                            attempt + 1,
                            _MAX_RATE_LIMIT_RETRIES,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        attempt += 1
                        continue
                    raise
                except ServerError:
                    if _should_retry_server_error(method, attempt):
                        logger.warning(
                            "Server error %d, retry %d/%d in %.1fs",
                            response.status_code,
                            attempt + 1,
                            _MAX_SERVER_ERROR_RETRIES,
                            _SERVER_ERROR_DELAY,
                        )
                        await asyncio.sleep(_SERVER_ERROR_DELAY)
                        attempt += 1
                        continue
                    raise

                return response

            except (httpx.ConnectError, httpx.ReadError, httpx.WriteError) as exc:
                if _should_retry_connection(method, attempt):
                    delay = _CONNECTION_BASE_DELAY * (2**attempt)
                    logger.warning(
                        "Connection error (%s), retry %d/%d in %.1fs",
                        type(exc).__name__,
                        attempt + 1,
                        _MAX_CONNECTION_RETRIES,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    attempt += 1
                    continue
                raise ConnectionError(str(exc)) from exc
            except httpx.TimeoutException as exc:
                if method == "GET" and attempt < _MAX_CONNECTION_RETRIES:
                    delay = _RATE_LIMIT_BASE_DELAY * (2**attempt)
                    logger.warning(
                        "Timeout on GET, retry %d/%d in %.1fs",
                        attempt + 1,
                        _MAX_CONNECTION_RETRIES,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    attempt += 1
                    continue
                raise ConnectionError(str(exc)) from exc

    async def close(self) -> None:
        await self._client.aclose()
