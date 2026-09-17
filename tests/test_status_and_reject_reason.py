"""``GET cloud-servers/{id}/status/`` payload and ``reason`` in create refusals.

Server-side sources (branch ``feature/pricing-plans-revision``):

* ``retrieve_server_can_start`` in ``website/user_panel/views/views.py`` returns
  ``can_start``, ``is_enough_money_for_full_period``,
  ``affordable_runtime_seconds``, ``remaining_monthly_seconds`` and, since the
  pricing-plans revision, ``launch_required_rub_cents`` (``None`` when the
  server cannot be started: the server does not compute it then).
* ``CloudConfigurationViewSet.create`` puts ``reason`` next to ``detail`` in
  its own 400 (``cpu_limit``) and 409 (``queue_disabled``) bodies (MIAN-412).
  DRF validation errors (400 with field errors) carry no ``reason``.
"""

import pytest
import respx

from intelion_cloud import IntelionCloud, ServerCreateRejectReason
from intelion_cloud.exceptions import APIError, ConflictError, ValidationError
from intelion_cloud.models import ServerStatus

from .conftest import API_URL, BASE_URL, SAMPLE_CLOUD_SERVER

STATUS_CAN_START = {
    "can_start": True,
    "is_enough_money_for_full_period": True,
    "affordable_runtime_seconds": 7200,
    "remaining_monthly_seconds": 1_000_000,
    "launch_required_rub_cents": 650_000,
}

STATUS_CANNOT_START = {
    "can_start": False,
    "is_enough_money_for_full_period": 0,
    "affordable_runtime_seconds": 0,
    "remaining_monthly_seconds": 0,
    "launch_required_rub_cents": None,
}


class TestServerStatusModel:
    def test_parses_every_field_the_view_returns(self):
        status = ServerStatus.from_dict(STATUS_CAN_START)
        assert status.can_start is True
        assert status.is_enough_money_for_full_period is True
        assert status.affordable_runtime_seconds == 7200
        assert status.remaining_monthly_seconds == 1_000_000
        assert status.launch_required_rub_cents == 650_000

    def test_cannot_start_keeps_launch_required_none(self):
        """``None`` must survive: ``0`` would read as "the start is free"."""
        status = ServerStatus.from_dict(STATUS_CANNOT_START)
        assert status.can_start is False
        assert status.is_enough_money_for_full_period is False
        assert status.launch_required_rub_cents is None

    def test_powered_off_under_term_requires_zero(self):
        """An open act already covers the start: the server sends ``0``, not ``None``."""
        status = ServerStatus.from_dict({**STATUS_CAN_START, "launch_required_rub_cents": 0})
        assert status.launch_required_rub_cents == 0

    def test_old_server_payload_without_the_new_fields(self):
        status = ServerStatus.from_dict({"can_start": True, "affordable_runtime_seconds": 60})
        assert status.can_start is True
        assert status.is_enough_money_for_full_period is None
        assert status.remaining_monthly_seconds is None
        assert status.launch_required_rub_cents is None


class TestGetStatusResource:
    @respx.mock(base_url=API_URL)
    def test_get_status_exposes_launch_required(self, respx_mock):
        respx_mock.get("cloud-servers/42/status/").respond(200, json=STATUS_CAN_START)
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        status = client.cloud_servers.get_status(42)
        assert status.launch_required_rub_cents == 650_000
        assert status.remaining_monthly_seconds == 1_000_000
        client.close()


class TestCreateRejectReason:
    @respx.mock(base_url=API_URL)
    def test_cpu_limit_400_carries_reason(self, respx_mock):
        respx_mock.post("cloud-servers/").respond(
            400,
            json={
                "detail": "Достигнут лимит серверов без GPU.",
                "reason": ServerCreateRejectReason.CPU_LIMIT,
            },
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(ValidationError) as exc_info:
            client.cloud_servers.create(name="x", flavor_id=1, ssd_count=50, os_id=1)
        assert exc_info.value.reason == "cpu_limit"
        assert exc_info.value.reason == ServerCreateRejectReason.CPU_LIMIT
        client.close()

    @respx.mock(base_url=API_URL)
    def test_queue_disabled_409_carries_reason(self, respx_mock):
        respx_mock.post("cloud-servers/").respond(
            409,
            json={
                "queue_disabled": True,
                "reason": ServerCreateRejectReason.QUEUE_DISABLED,
                "detail": "Очередь на RTX 4090 недоступна.",
                "suggested_alternative": None,
            },
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(ConflictError) as exc_info:
            client.cloud_servers.create(name="x", flavor_id=1, ssd_count=50, os_id=1, is_in_queue=True)
        assert exc_info.value.reason == "queue_disabled"
        assert exc_info.value.response_body["queue_disabled"] is True
        client.close()

    @respx.mock(base_url=API_URL)
    def test_drf_validation_error_has_no_reason(self, respx_mock):
        """Field errors are a dict without ``reason``: the property is ``None``, not a crash."""
        respx_mock.post("cloud-servers/").respond(400, json={"name": ["This field is required."]})
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(ValidationError) as exc_info:
            client.cloud_servers.create(name="", flavor_id=1, ssd_count=50, os_id=1)
        assert exc_info.value.reason is None
        assert exc_info.value.field_errors == {"name": ["This field is required."]}
        client.close()

    def test_reason_is_none_for_non_dict_and_non_string_bodies(self):
        assert APIError("x", status_code=500, response_body="html").reason is None
        assert APIError("x", status_code=400, response_body={"reason": 7}).reason is None
        assert APIError("x", status_code=400, response_body={"reason": ""}).reason is None
