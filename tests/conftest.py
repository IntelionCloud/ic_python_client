"""Shared fixtures for tests."""

import pytest
import respx

from intelion_cloud import IntelionCloud

BASE_URL = "https://test.intelion.cloud"
API_URL = f"{BASE_URL}/api/v2/"


@pytest.fixture
def mock_api():
    """Provide a respx mock router scoped to the test API URL."""
    with respx.mock(base_url=API_URL) as router:
        yield router


@pytest.fixture
def client():
    """Create a test client with a fake token."""
    c = IntelionCloud(token="test-token-123", base_url=BASE_URL, timeout=5.0)
    yield c
    c.close()


# --- Sample response data ---

SAMPLE_GPU = {
    "id": 1,
    "name": "NVIDIA H100",
    "slug": "nvidia-h100",
    "group_title": "g",
    "cuda_cores": 16896,
    "tensor_cores": 528,
    "ram": 80,
    "ram_type": "HBM3",
    "is_cloud": True,
    "monthly_price_rub_cents": 10000000,
    "hourly_price_rub_cents": 14880,
    "daily_price_rub_cents": 357142,
    "monthly_price_rub": "100000.00",
    "hourly_price_rub": "148.80",
    "daily_price_rub": "3571.42",
    "discount_percent": 0,
}

SAMPLE_CPU = {
    "id": 1,
    "name": "AMD EPYC 9454",
    "cores": 48,
    "threads": 96,
    "monthly_price_rub_cents": 500000,
    "hourly_price_rub_cents": 744,
    "daily_price_rub_cents": 17857,
    "group_title": "g",
}

SAMPLE_RAM = {
    "id": 1,
    "size": 64,
    "is_ecc": True,
    "standard": 5,
    "monthly_price_rub_cents": 200000,
    "hourly_price_rub_cents": 297,
    "daily_price_rub_cents": 7142,
    "group_title": "g",
}

SAMPLE_SSD = {
    "id": 1,
    "size": 1024,
    "group_title": "nvme4",
    "monthly_price_rub_cents": 100000,
    "hourly_price_rub_cents": 148,
    "daily_price_rub_cents": 3571,
}

SAMPLE_OS_IMAGE = {
    "id": 1,
    "name": "Ubuntu 22.04 LTS",
    "type": "lin",
    "description": "Ubuntu Server",
    "ssh_enabled": True,
    "rdp_enabled": False,
    "compatible_flavor_ids": [],
}

SAMPLE_FLAVOR = {
    "id": 1,
    "openstack_id": "abc-def-123",
    "name": "1x H100 80GB",
    "cpu_count": 16,
    "ram_count": 128,
    "gpu_count": 1,
    "flavor_monthly_price_rub_cents": 10800000,
    "flavor_hourly_price_rub_cents": 16069,
    "max_available": 5,
    "cpu": SAMPLE_CPU,
    "ram": SAMPLE_RAM,
    "gpu": SAMPLE_GPU,
}

SAMPLE_SOFTWARE_ADDON = {
    "uca_id": 555,
    "id": 7,
    "name": "ComfyUI",
    "port": 8188,
    "status": "INSTALLING",
    "access_token": "tkn-abc",
    "progress_message": "Downloading weights...",
    "error_message": "",
    "hardware_mode": "GPU",
    "last_heartbeat_dt": "2026-04-21T12:00:00Z",
    "has_error": False,
}

SAMPLE_USAGE_ACT = {
    "id": 100,
    "user_config_id": 42,
    "start_dt": "2025-01-01T00:00:00Z",
    "stop_dt": None,
    "monthly_price_rub": "108000.00",
    "daily_price_rub": "3857.14",
    "hourly_price_rub": "160.71",
    "period": 0,
    "periods_planned": 1,
    "cloud_server_uptime_seconds": 3600,
    "cloud_srv_price_rub_cents": 16071,
    "actual_cost_rub_cents": 16071,
    "spent_amount_rub_cents": 16071,
    "refund_amount_rub_cents": 0,
    "next_payment": {
        "period_price_rub_cents": 16071,
        "periods_to_pay": 1,
        "amount_rub_cents": 16071,
        "period_end_dt": "2025-01-01T01:00:00Z",
    },
}

SAMPLE_CLOUD_SERVER = {
    "id": 42,
    "name": "my-gpu-server",
    "status": 2,
    "price_plan": 0,
    "is_auto_renewal": True,
    "monthly_price_rub_cents": 10800000,
    "hourly_price_rub_cents": 16069,
    "server_full_rent_price_rub_cents": 10800000,
    "flavor_oid": "abc-def-123",
    "server_state": 0,
    "has_instance": True,
    "credentials": "SSH",
    "ip_to_connect": "10.0.0.1",
    "domain_to_connect": "server42.intelion.cloud",
    "login": "root",
    "gpu": SAMPLE_GPU,
    "gpu_count": 1,
    "cpu": SAMPLE_CPU,
    "cpu_count": 16,
    "ram": SAMPLE_RAM,
    "ram_count": 2,
    "network_disk": SAMPLE_SSD,
    "network_disk_count": 1,
    "os": SAMPLE_OS_IMAGE,
    "usage_act": SAMPLE_USAGE_ACT,
    "last_finished_usage_act": None,
    "last_usage_act": SAMPLE_USAGE_ACT,
    "promocode": None,
    "physical_server": None,
    "white_ips": [{"address_v4": "10.0.0.1"}],
    "software_addons": [SAMPLE_SOFTWARE_ADDON],
    "card_background": "https://cdn.intelion.cloud/bg/42.png",
    "monthly_price_rub": "108000.00",
    "total_ram_size": 128,
    "total_network_disk_size": 1024,
    "total_local_disk_size": 0,
    "max_available": 5,
}

SAMPLE_INFERENCE_API_KEY = {
    "id": "a" * 64,
    "key_hash": "a" * 64,
    "name": "prod-agent",
    "prefix": "ic-aaaaaa",
    "rate_limit_rpm": 60,
    "is_active": True,
    "disabled_reason": "",
    "credit_limit_rub_cents": None,
    "spent_rub_cents": 0,
    "free_tokens_consumed": 0,
    "limit_reset_period": "",
    "allowed_models": None,
    "compaction_enabled": True,
    "residency": "",
    "expires_at": None,
    "created_at": "2026-05-01T00:00:00+00:00",
    "last_used_at": None,
    "last_request_ip": None,
}

SAMPLE_USER = {
    "id": 7,
    "username": "testuser",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "current_balance_rub_cents": 5000000,
    "held_up_money_rub_cents": 100000,
    "is_phone_verified": True,
    "is_staff": False,
    "legal": "PERSON_TYPE",
    "company_name": "",
    "card_number": "6411",
    "default_payment_type": "ACQUIRING_TYPE",
    "tg_id": True,
    "is_email_verified": True,
}
