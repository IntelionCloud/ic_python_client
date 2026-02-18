"""Tests for JSON -> dataclass model parsing."""

from intelion_cloud.models import (
    CPU,
    GPU,
    HDD,
    OSImage,
    RAM,
    SSD,
    CloudServer,
    DebtInfo,
    Flavor,
    Promocode,
    ServerStatus,
    UsageAct,
    User,
    WhiteIP,
)

from .conftest import (
    SAMPLE_CLOUD_SERVER,
    SAMPLE_CPU,
    SAMPLE_FLAVOR,
    SAMPLE_GPU,
    SAMPLE_OS_IMAGE,
    SAMPLE_RAM,
    SAMPLE_SSD,
    SAMPLE_USAGE_ACT,
    SAMPLE_USER,
)


class TestGPU:
    def test_from_dict(self):
        gpu = GPU.from_dict(SAMPLE_GPU)
        assert gpu.id == 1
        assert gpu.name == "NVIDIA H100"
        assert gpu.slug == "nvidia-h100"
        assert gpu.cuda_cores == 16896
        assert gpu.tensor_cores == 528
        assert gpu.ram == 80
        assert gpu.ram_type == "HBM3"
        assert gpu.is_cloud is True
        assert gpu.monthly_price_rub_cents == 10000000
        assert gpu.hourly_price_rub_cents == 14880

    def test_from_dict_minimal(self):
        gpu = GPU.from_dict({"id": 2, "name": "RTX 4090"})
        assert gpu.id == 2
        assert gpu.name == "RTX 4090"
        assert gpu.cuda_cores == 0
        assert gpu.is_cloud is False


class TestCPU:
    def test_from_dict(self):
        cpu = CPU.from_dict(SAMPLE_CPU)
        assert cpu.id == 1
        assert cpu.name == "AMD EPYC 9454"
        assert cpu.cores == 48
        assert cpu.threads == 96


class TestRAM:
    def test_from_dict(self):
        ram = RAM.from_dict(SAMPLE_RAM)
        assert ram.id == 1
        assert ram.size == 64
        assert ram.is_ecc is True
        assert ram.standard == 5


class TestSSD:
    def test_from_dict(self):
        ssd = SSD.from_dict(SAMPLE_SSD)
        assert ssd.id == 1
        assert ssd.size == 1024
        assert ssd.group_title == "nvme4"


class TestOSImage:
    def test_from_dict(self):
        img = OSImage.from_dict(SAMPLE_OS_IMAGE)
        assert img.id == 1
        assert img.name == "Ubuntu 22.04 LTS"
        assert img.type == "lin"
        assert img.ssh_enabled is True
        assert img.rdp_enabled is False


class TestFlavor:
    def test_from_dict_with_nested(self):
        flavor = Flavor.from_dict(SAMPLE_FLAVOR)
        assert flavor.id == "abc-def-123"
        assert flavor.name == "1x H100 80GB"
        assert flavor.cpu_count == 16
        assert flavor.ram_count == 128.0
        assert flavor.gpu_count == 1
        assert flavor.max_available == 5
        # Nested models
        assert flavor.gpu is not None
        assert flavor.gpu.name == "NVIDIA H100"
        assert flavor.cpu is not None
        assert flavor.cpu.name == "AMD EPYC 9454"
        assert flavor.ram is not None
        assert flavor.ram.size == 64

    def test_from_dict_no_gpu(self):
        data = {**SAMPLE_FLAVOR, "gpu": None, "gpu_count": None}
        flavor = Flavor.from_dict(data)
        assert flavor.gpu is None
        assert flavor.gpu_count is None


class TestUsageAct:
    def test_from_dict(self):
        act = UsageAct.from_dict(SAMPLE_USAGE_ACT)
        assert act.id == 100
        assert act.user_config_id == 42
        assert act.cloud_server_uptime_seconds == 3600
        assert act.next_payment is not None
        assert act.next_payment.amount_rub_cents == 16071


class TestCloudServer:
    def test_from_dict_full(self):
        server = CloudServer.from_dict(SAMPLE_CLOUD_SERVER)
        assert server.id == 42
        assert server.name == "my-gpu-server"
        assert server.status == 2
        assert server.flavor_oid == "abc-def-123"
        assert server.has_instance is True
        assert server.ip_to_connect == "10.0.0.1"
        # Nested
        assert server.gpu is not None
        assert server.gpu.name == "NVIDIA H100"
        assert server.cpu is not None
        assert server.ram is not None
        assert server.network_disk is not None
        assert server.os is not None
        assert server.os.name == "Ubuntu 22.04 LTS"
        # Usage act
        assert server.usage_act is not None
        assert server.usage_act.id == 100
        # White IPs
        assert len(server.white_ips) == 1
        assert server.white_ips[0].address_v4 == "10.0.0.1"

    def test_from_dict_minimal(self):
        data = {
            "id": 1,
            "name": "test",
            "status": -2,
            "price_plan": 0,
            "is_auto_renewal": False,
            "monthly_price_rub_cents": 0,
            "hourly_price_rub_cents": 0,
            "server_full_rent_price_rub_cents": 0,
        }
        server = CloudServer.from_dict(data)
        assert server.id == 1
        assert server.gpu is None
        assert server.white_ips == []
        assert server.usage_act is None


class TestServerStatus:
    def test_from_dict(self):
        data = {"can_start": True, "affordable_runtime_seconds": 7200}
        status = ServerStatus.from_dict(data)
        assert status.can_start is True
        assert status.affordable_runtime_seconds == 7200


class TestUser:
    def test_from_dict(self):
        user = User.from_dict(SAMPLE_USER)
        assert user.id == 7
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.current_balance_rub_cents == 5000000
        assert user.is_phone_verified is True
        assert user.card_number == "6411"
        assert user.tg_id is True


class TestDebtInfo:
    def test_from_dict(self):
        data = {
            "period_price_rub_cents": 16071,
            "periods_to_pay": 2,
            "amount_rub_cents": 32142,
            "period_end_dt": "2025-01-02T00:00:00Z",
        }
        debt = DebtInfo.from_dict(data)
        assert debt.period_price_rub_cents == 16071
        assert debt.periods_to_pay == 2
        assert debt.amount_rub_cents == 32142


class TestPromocode:
    def test_from_dict(self):
        data = {"id": 5, "code": "WELCOME10", "discount_value": 10}
        promo = Promocode.from_dict(data)
        assert promo.id == 5
        assert promo.code == "WELCOME10"
        assert promo.discount_value == 10


class TestWhiteIP:
    def test_from_dict(self):
        ip = WhiteIP.from_dict({"address_v4": "192.168.1.1"})
        assert ip.address_v4 == "192.168.1.1"
