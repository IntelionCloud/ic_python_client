"""Tests for the inference_api_keys resource (AI API key management,
ТЗ ``tz-public-key-management-api.md``)."""

import respx
import json

import pytest

from intelion_cloud import IntelionCloud, NotFoundError, PaymentRequiredError, ForbiddenError

from .conftest import API_URL, BASE_URL, SAMPLE_INFERENCE_API_KEY


class TestList:
    @respx.mock(base_url=API_URL)
    def test_list_returns_keys(self, respx_mock):
        respx_mock.get("inference-api-keys/").respond(200, json=[SAMPLE_INFERENCE_API_KEY])
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        keys = client.inference_api_keys.list()
        assert len(keys) == 1
        assert keys[0].key_hash == "a" * 64
        assert keys[0].name == "prod-agent"
        client.close()

    @respx.mock(base_url=API_URL)
    def test_list_include_inactive(self, respx_mock):
        respx_mock.get("inference-api-keys/", params={"include_inactive": "true"}).respond(
            200, json=[SAMPLE_INFERENCE_API_KEY],
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        keys = client.inference_api_keys.list(include_inactive=True)
        assert len(keys) == 1
        client.close()


class TestGet:
    @respx.mock(base_url=API_URL)
    def test_get_filters_from_list(self, respx_mock):
        other = {**SAMPLE_INFERENCE_API_KEY, "id": "b" * 64, "key_hash": "b" * 64, "name": "other"}
        respx_mock.get("inference-api-keys/", params={"include_inactive": "true"}).respond(
            200, json=[SAMPLE_INFERENCE_API_KEY, other],
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        key = client.inference_api_keys.get("a" * 64)
        assert key.name == "prod-agent"
        client.close()

    @respx.mock(base_url=API_URL)
    def test_get_raises_not_found(self, respx_mock):
        respx_mock.get("inference-api-keys/", params={"include_inactive": "true"}).respond(200, json=[])
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(NotFoundError):
            client.inference_api_keys.get("a" * 64)
        client.close()


class TestCreate:
    @respx.mock(base_url=API_URL)
    def test_create_returns_raw_key_once(self, respx_mock):
        respx_mock.post("inference-api-keys/").respond(
            201, json={**SAMPLE_INFERENCE_API_KEY, "api_key": "ic-" + "1" * 32},
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        key = client.inference_api_keys.create(name="prod-agent", rate_limit_rpm=120)
        assert key.api_key == "ic-" + "1" * 32
        body = json.loads(respx_mock.calls[0].request.content)
        assert body["name"] == "prod-agent"
        assert body["rate_limit_rpm"] == 120
        assert body["save_to_secrets_manager"] is False
        client.close()

    @respx.mock(base_url=API_URL)
    def test_create_forbidden_without_access(self, respx_mock):
        respx_mock.post("inference-api-keys/").respond(
            403,
            json={
                "detail": "AI API доступен только пользователям, открывшим бету.",
                "code": "aiapi_access_not_granted",
                "how_to": "POST /api/v2/inference-api-keys/access/",
                "threshold_rub_cents": 100000,
            },
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(ForbiddenError) as exc_info:
            client.inference_api_keys.create(name="x")
        assert exc_info.value.response_body["code"] == "aiapi_access_not_granted"
        assert exc_info.value.response_body["threshold_rub_cents"] == 100000
        client.close()


class TestUpdate:
    @respx.mock(base_url=API_URL)
    def test_update_sends_only_provided_fields(self, respx_mock):
        respx_mock.patch(f"inference-api-keys/{'a' * 64}/").respond(
            200, json={**SAMPLE_INFERENCE_API_KEY, "name": "renamed"},
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        key = client.inference_api_keys.update("a" * 64, name="renamed")
        assert key.name == "renamed"
        body = json.loads(respx_mock.calls[0].request.content)
        assert body == {"name": "renamed"}
        client.close()


class TestRevoke:
    @respx.mock(base_url=API_URL)
    def test_revoke_204(self, respx_mock):
        respx_mock.delete(f"inference-api-keys/{'a' * 64}/").respond(204)
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        assert client.inference_api_keys.revoke("a" * 64) is None
        client.close()


class TestRotate:
    @respx.mock(base_url=API_URL)
    def test_rotate_returns_new_and_old(self, respx_mock):
        respx_mock.post(f"inference-api-keys/{'a' * 64}/rotate/").respond(
            201,
            json={
                **SAMPLE_INFERENCE_API_KEY, "key_hash": "b" * 64, "id": "b" * 64,
                "api_key": "ic-" + "2" * 32,
                "old_key": {"key_hash": "a" * 64, "name": "prod-agent-old-20260515", "expires_at": "2026-05-16T00:00:00+00:00"},
            },
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        result = client.inference_api_keys.rotate("a" * 64, grace_period_hours=24)
        assert result.new_key.key_hash == "b" * 64
        assert result.new_key.api_key == "ic-" + "2" * 32
        assert result.old_key_hash == "a" * 64
        assert result.old_expires_at == "2026-05-16T00:00:00+00:00"
        body = json.loads(respx_mock.calls[0].request.content)
        assert body["grace_period_hours"] == 24
        client.close()


class TestUsage:
    @respx.mock(base_url=API_URL)
    def test_usage_windows(self, respx_mock):
        respx_mock.get(f"inference-api-keys/{'a' * 64}/usage/").respond(
            200,
            json={
                "key_hash": "a" * 64, "spent_rub_cents": 500, "free_tokens_consumed": 100,
                "7d": {"input_tokens": 10, "output_tokens": 20, "cost_rub_cents": 300,
                       "request_count": 2, "top_models": [{"model_slug": "gpt-x", "cost_rub_cents": 300, "request_count": 2}]},
            },
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        usage = client.inference_api_keys.usage("a" * 64)
        assert usage.spent_rub_cents == 500
        assert usage.window_7d.cost_rub_cents == 300
        assert usage.window_7d.top_models[0].model_slug == "gpt-x"
        assert usage.window_30d is None
        client.close()


class TestUsageRange:
    @respx.mock(base_url=API_URL)
    def test_usage_range_json(self, respx_mock):
        respx_mock.get("inference-api-keys/usage-range/").respond(
            200,
            json={
                "date_from": "2026-05-15", "date_to": "2026-05-16", "total_rub_cents": 600,
                "rows": [{
                    "key_hash": "a" * 64, "key_name": "prod-agent", "is_active": True,
                    "deleted": False, "model_slug": "gpt-x", "display_name": "GPT-X",
                    "kind": "model", "date": "2026-05-15", "requests": 3,
                    "input_tokens": 100, "output_tokens": 50, "cache_creation_tokens": 0,
                    "cache_read_tokens": 0, "free_tokens_consumed": 0, "billed_rub_cents": 600,
                }],
            },
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        usage = client.inference_api_keys.usage_range(date_from="2026-05-15", date_to="2026-05-16")
        assert usage.total_rub_cents == 600
        assert usage.rows[0].key_hash == "a" * 64
        assert usage.rows[0].display_name == "GPT-X"
        client.close()

    @respx.mock(base_url=API_URL)
    def test_usage_range_csv_returns_raw_text(self, respx_mock):
        csv_body = "﻿key_hash,billed_rub_cents\r\n" + ("a" * 64) + ",600\r\n"
        respx_mock.get("inference-api-keys/usage-range/").respond(
            200, text=csv_body, headers={"Content-Type": "text/csv; charset=utf-8"},
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        csv_text = client.inference_api_keys.usage_range_csv(date_from="2026-05-15", date_to="2026-05-16")
        assert "billed_rub_cents" in csv_text
        assert "a" * 64 in csv_text
        # Accept header sent so the server's format negotiation doesn't 406.
        assert respx_mock.calls[0].request.headers["accept"] == "text/csv"
        client.close()


class TestModels:
    @respx.mock(base_url=API_URL)
    def test_models_returns_raw_catalog(self, respx_mock):
        respx_mock.get("inference-api-keys/models/").respond(
            200, json=[{"slug": "gpt-x", "name": "GPT-X", "context_length": 128000}],
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        catalog = client.inference_api_keys.models()
        assert catalog[0]["slug"] == "gpt-x"
        client.close()


class TestAccess:
    @respx.mock(base_url=API_URL)
    def test_access_status_not_granted(self, respx_mock):
        respx_mock.get("inference-api-keys/access/").respond(
            200,
            json={"granted": False, "visible_balance_rub_cents": 75000,
                  "threshold_rub_cents": 100000, "shortfall_rub_cents": 25000},
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        status = client.inference_api_keys.access_status()
        assert status.granted is False
        assert status.shortfall_rub_cents == 25000
        client.close()

    @respx.mock(base_url=API_URL)
    def test_request_access_raises_payment_required(self, respx_mock):
        respx_mock.post("inference-api-keys/access/").respond(
            402,
            json={"granted": False, "threshold_rub_cents": 100000,
                  "visible_balance_rub_cents": 75000, "shortfall_rub_cents": 25000,
                  "detail": "Для открытия AI API нужно пополнить баланс ещё на 250.00 ₽."},
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        with pytest.raises(PaymentRequiredError) as exc_info:
            client.inference_api_keys.request_access()
        assert exc_info.value.response_body["shortfall_rub_cents"] == 25000
        client.close()

    @respx.mock(base_url=API_URL)
    def test_request_access_granted(self, respx_mock):
        respx_mock.post("inference-api-keys/access/").respond(
            200, json={"granted": True, "threshold_rub_cents": 100000},
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        status = client.inference_api_keys.request_access()
        assert status.granted is True
        client.close()
