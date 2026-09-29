"""Auto-renewal under a rental term: 409 refusals of ``update`` and ``start``.

Server-side sources (branch ``feature/pricing-plans-revision``):

* ``assert_auto_renewal_change_allowed`` in
  ``website/user_panel/services/term_obligation.py`` guards
  ``PATCH cloud-servers/{id}/``: turning auto-renewal off is always allowed;
  turning it on under a running confirmed term is 409
  ``AUTO_RENEWAL_CONSENT_REQUIRED`` (only the customer in the web panel can do
  it); under ``pending_consent`` or an ended, not stopped term it
  is 409 ``AUTO_RENEWAL_NOT_APPLICABLE``.
* ``apply_auto_renewal_on_start``: under ``is_bound_by_term`` the start keeps
  the toggle from the signed document and ignores ``isAutoRenewal``.
* ``assert_term_start_allowed``: a start inside the term rollover window is
  409 ``TERM_RENEWAL_IN_PROGRESS``.

All three bodies are ``TermStartRefused.as_payload()``:
``{"error_code", "message", "detail"}``.
"""

import json

import pytest
import respx

from intelion_cloud import AsyncIntelionCloud, IntelionCloud, TermConflictCode
from intelion_cloud.exceptions import APIError, ConflictError, ValidationError

from .conftest import API_URL, BASE_URL, SAMPLE_CLOUD_SERVER, SAMPLE_TERM_SERVER

CONSENT_MESSAGE = (
    "Включение автопродления продлевает срок аренды: подтвердите условия "
    "продления в окне автопродления на карточке сервера."
)
PENDING_MESSAGE = (
    "Автопродление для этого срока выбрано при подтверждении условий. "
    "Изменить его можно после запуска сервера."
)
EXPIRED_MESSAGE = (
    "Срок аренды уже закончился: включить автопродление для него нельзя. "
    "Новый срок начнётся с нового подтверждения условий при запуске."
)
ROLLOVER_MESSAGE = "Срок аренды сейчас продлевается. Повторите запуск через минуту."


def _refusal(code: str, message: str) -> dict:
    """The exact body the server builds (``TermStartRefused.as_payload``)."""
    return {"error_code": code, "message": message, "detail": message}


class TestTermConflictCode:
    def test_values_mirror_the_server_constants(self):
        assert TermConflictCode.AUTO_RENEWAL_CONSENT_REQUIRED == "AUTO_RENEWAL_CONSENT_REQUIRED"
        assert TermConflictCode.AUTO_RENEWAL_NOT_APPLICABLE == "AUTO_RENEWAL_NOT_APPLICABLE"
        assert TermConflictCode.TERM_RENEWAL_IN_PROGRESS == "TERM_RENEWAL_IN_PROGRESS"


class TestErrorCodeProperty:
    def test_reads_error_code_from_a_term_refusal(self):
        exc = ConflictError(
            "x",
            status_code=409,
            response_body=_refusal(TermConflictCode.AUTO_RENEWAL_NOT_APPLICABLE, "m"),
        )
        assert exc.error_code == "AUTO_RENEWAL_NOT_APPLICABLE"

    @pytest.mark.parametrize(
        "body",
        [
            None,
            "<html>502</html>",
            {"detail": "Сервер занят другой операцией."},
            {"error_code": 7},
            {"error_code": ""},
            {"error_code": None},
            ["not", "a", "dict"],
        ],
    )
    def test_is_none_without_a_usable_string_code(self, body):
        assert APIError("x", status_code=409, response_body=body).error_code is None

    def test_reason_and_error_code_do_not_leak_into_each_other(self):
        """A queue refusal carries ``reason``, a term refusal ``error_code``: never both by guess."""
        queue = ConflictError(
            "x", status_code=409, response_body={"reason": "queue_disabled", "detail": "d"}
        )
        term = ConflictError(
            "x",
            status_code=409,
            response_body=_refusal(TermConflictCode.TERM_RENEWAL_IN_PROGRESS, "m"),
        )
        assert queue.error_code is None
        assert term.reason is None


class TestUpdateAutoRenewalUnderTerm:
    @respx.mock(base_url=API_URL)
    def test_turning_on_under_confirmed_term_needs_consent(self, respx_mock):
        route = respx_mock.patch("cloud-servers/42/").respond(
            409, json=_refusal(TermConflictCode.AUTO_RENEWAL_CONSENT_REQUIRED, CONSENT_MESSAGE)
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(ConflictError) as exc_info:
            client.cloud_servers.update(42, is_auto_renewal=True)
        exc = exc_info.value
        assert exc.status_code == 409
        assert exc.error_code == TermConflictCode.AUTO_RENEWAL_CONSENT_REQUIRED
        assert str(exc) == CONSENT_MESSAGE
        assert not isinstance(exc, ValidationError)
        assert json.loads(route.calls[0].request.content) == {"is_auto_renewal": True}
        # A 409 is a state conflict, not a transient failure: no retry.
        assert route.call_count == 1
        client.close()

    @pytest.mark.parametrize("message", [PENDING_MESSAGE, EXPIRED_MESSAGE])
    @respx.mock(base_url=API_URL)
    def test_turning_on_while_toggle_is_fixed_by_a_document(self, respx_mock, message):
        """``pending_consent`` and an ended, not stopped term share one code, two messages."""
        respx_mock.patch("cloud-servers/42/").respond(
            409, json=_refusal(TermConflictCode.AUTO_RENEWAL_NOT_APPLICABLE, message)
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(ConflictError) as exc_info:
            client.cloud_servers.update(42, is_auto_renewal=True)
        assert exc_info.value.error_code == TermConflictCode.AUTO_RENEWAL_NOT_APPLICABLE
        assert str(exc_info.value) == message
        client.close()

    @respx.mock(base_url=API_URL)
    def test_message_is_read_from_message_when_detail_is_absent(self, respx_mock):
        """Bodies without ``detail`` (older builds of the guard) still give the user text."""
        respx_mock.patch("cloud-servers/42/").respond(
            409,
            json={
                "error_code": TermConflictCode.AUTO_RENEWAL_CONSENT_REQUIRED,
                "message": CONSENT_MESSAGE,
            },
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(ConflictError) as exc_info:
            client.cloud_servers.update(42, is_auto_renewal=True)
        assert str(exc_info.value) == CONSENT_MESSAGE
        assert exc_info.value.error_code == TermConflictCode.AUTO_RENEWAL_CONSENT_REQUIRED
        client.close()

    @respx.mock(base_url=API_URL)
    def test_turning_off_under_confirmed_term_is_accepted(self, respx_mock):
        route = respx_mock.patch("cloud-servers/42/").respond(
            200, json={**SAMPLE_TERM_SERVER, "is_auto_renewal": False}
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        server = client.cloud_servers.update(42, is_auto_renewal=False)
        assert server.is_auto_renewal is False
        assert server.is_renewal_mandatory is True
        assert json.loads(route.calls[0].request.content) == {"is_auto_renewal": False}
        client.close()

    @respx.mock(base_url=API_URL)
    def test_turning_on_off_a_term_is_unchanged(self, respx_mock):
        respx_mock.patch("cloud-servers/42/").respond(
            200, json={**SAMPLE_CLOUD_SERVER, "is_auto_renewal": True}
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        server = client.cloud_servers.update(42, is_auto_renewal=True)
        assert server.is_auto_renewal is True
        assert server.term_state == "not_term_plan"
        client.close()

    @respx.mock(base_url=API_URL)
    def test_rename_alone_does_not_send_the_toggle(self, respx_mock):
        """``None`` means "leave as is": the guard must not be triggered by a rename."""
        route = respx_mock.patch("cloud-servers/42/").respond(200, json=SAMPLE_TERM_SERVER)
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        client.cloud_servers.update(42, name="renamed")
        assert json.loads(route.calls[0].request.content) == {"name": "renamed"}
        client.close()

    @pytest.mark.asyncio
    async def test_async_update_raises_the_same_conflict(self):
        async with respx.mock(base_url=API_URL) as respx_mock:
            respx_mock.patch("cloud-servers/42/").respond(
                409,
                json=_refusal(TermConflictCode.AUTO_RENEWAL_CONSENT_REQUIRED, CONSENT_MESSAGE),
            )
            async with AsyncIntelionCloud(token="tok", base_url=BASE_URL) as client:
                with pytest.raises(ConflictError) as exc_info:
                    await client.cloud_servers.update(42, is_auto_renewal=True)
        assert exc_info.value.error_code == TermConflictCode.AUTO_RENEWAL_CONSENT_REQUIRED


class TestStartUnderTerm:
    @respx.mock(base_url=API_URL)
    def test_start_under_term_returns_the_signed_toggle(self, respx_mock):
        """The server ignores ``isAutoRenewal`` under a term; the SDK reports what it got back."""
        route = respx_mock.post("cloud-servers/42/actions/").respond(
            200, json={**SAMPLE_TERM_SERVER, "is_auto_renewal": True}
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        server = client.cloud_servers.start(42, is_auto_renewal=False)
        body = json.loads(route.calls[0].request.content)
        assert body == {"status": 2, "isAutoRenewal": False}
        assert server.is_auto_renewal is True
        assert server.is_bound_by_term is True
        client.close()

    @respx.mock(base_url=API_URL)
    def test_start_during_term_rollover_is_a_conflict(self, respx_mock):
        route = respx_mock.post("cloud-servers/42/actions/").respond(
            409, json=_refusal(TermConflictCode.TERM_RENEWAL_IN_PROGRESS, ROLLOVER_MESSAGE)
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(ConflictError) as exc_info:
            client.cloud_servers.start(42)
        assert exc_info.value.error_code == TermConflictCode.TERM_RENEWAL_IN_PROGRESS
        assert str(exc_info.value) == ROLLOVER_MESSAGE
        # POST is not idempotent: the SDK never retries it on its own.
        assert route.call_count == 1
        client.close()

    @respx.mock(base_url=API_URL)
    def test_busy_server_conflict_has_no_error_code(self, respx_mock):
        """The pre-existing 409 (server busy) keeps working and is told apart by ``error_code``."""
        respx_mock.post("cloud-servers/42/actions/").respond(
            409, json={"detail": "Сервер занят другой операцией."}
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(ConflictError) as exc_info:
            client.cloud_servers.start(42)
        assert exc_info.value.error_code is None
        assert str(exc_info.value) == "Сервер занят другой операцией."
        client.close()
