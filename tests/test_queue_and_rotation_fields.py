"""Fields the API v2 serializers return but the SDK used to drop silently.

Server-side sources:
  * ``queue_disabled`` / ``suggested_alternative`` — ``FlavorConfigSerializer``
    and ``UserConfigurationSerializer`` (PR #526);
  * ``password_rotation`` — ``UserConfigurationSerializer`` (incident 2026-07-29);
  * ``maintenance_reason`` — ``UserConfiguration`` model field;
  * ``cuda_version`` — ``OperationalSystemImageSerializer``.

Note the shapes are asserted against the real serializers, not against the
published OpenAPI schema: drf-spectacular types every ``SerializerMethodField``
as ``string``, so the schema claims ``queue_disabled`` is a string and
``suggested_alternative``/``password_rotation`` are strings too, while they are
in fact a bool and two nested objects.
"""

from intelion_cloud.models import CloudServer, Flavor, FlavorSubstitution, OSImage

SUBSTITUTION = {
    "flavor_id": 42,
    "flavor_name": "RTX 4090 x1",
    "gpu_id": 7,
    "gpu_slug": "nvidia-rtx-4090",
    "gpu_name": "NVIDIA RTX 4090",
    "gpu_ram": 24,
    "gpu_count": 1,
    "cpu_id": 3,
    "cpu_count": 8,
    "ram_id": 5,
    "ram_count": 32,
    "monthly_price_rub_cents": 4500000,
    "hourly_price_rub_cents": 6800,
    "exact_match": False,
}


class TestFlavorSubstitution:
    def test_from_dict(self):
        sub = FlavorSubstitution.from_dict(SUBSTITUTION)
        assert sub.flavor_id == 42
        assert sub.gpu_slug == "nvidia-rtx-4090"
        assert sub.monthly_price_rub_cents == 4500000
        assert sub.exact_match is False

    def test_exact_match_defaults_to_true(self):
        payload = {k: v for k, v in SUBSTITUTION.items() if k != "exact_match"}
        assert FlavorSubstitution.from_dict(payload).exact_match is True


class TestFlavorQueueFields:
    def test_queue_disabled_with_alternative(self):
        flavor = Flavor.from_dict({
            "id": 1,
            "name": "H100 x8",
            "cpu_count": 64,
            "ram_count": 512,
            "gpu_count": 8,
            "flavor_monthly_price_rub_cents": 100,
            "flavor_hourly_price_rub_cents": 1,
            "max_available": 0,
            "queue_disabled": True,
            "suggested_alternative": SUBSTITUTION,
        })
        assert flavor.queue_disabled is True
        assert flavor.suggested_alternative is not None
        assert flavor.suggested_alternative.flavor_name == "RTX 4090 x1"

    def test_absent_fields_do_not_break_old_payloads(self):
        """Старый сервер (или урезанный ответ) не должен ронять парсинг."""
        flavor = Flavor.from_dict({
            "id": 1,
            "name": "A100 x1",
            "cpu_count": 8,
            "ram_count": 64,
            "gpu_count": 1,
            "flavor_monthly_price_rub_cents": 100,
            "flavor_hourly_price_rub_cents": 1,
            "max_available": 3,
        })
        assert flavor.queue_disabled is False
        assert flavor.suggested_alternative is None

    def test_null_alternative_stays_none(self):
        flavor = Flavor.from_dict({
            "id": 1,
            "name": "A100 x1",
            "cpu_count": 8,
            "ram_count": 64,
            "gpu_count": 1,
            "flavor_monthly_price_rub_cents": 100,
            "flavor_hourly_price_rub_cents": 1,
            "max_available": 3,
            "queue_disabled": True,
            "suggested_alternative": None,
        })
        assert flavor.queue_disabled is True
        assert flavor.suggested_alternative is None


def _server(**extra):
    base = {
        "id": 8564,
        "name": "srv",
        "status": 1,
        "price_plan": 1,
        "is_auto_renewal": True,
        "monthly_price_rub_cents": 100,
        "hourly_price_rub_cents": 1,
        "server_full_rent_price_rub_cents": 100,
    }
    base.update(extra)
    return CloudServer.from_dict(base)


class TestCloudServerNewFields:
    def test_password_rotation_rotated(self):
        srv = _server(password_rotation={
            "status": "rotated",
            "rotated_at": "2026-07-29T12:00:00+00:00",
            "acknowledged": False,
        })
        assert srv.password_rotation is not None
        assert srv.password_rotation.status == "rotated"
        assert srv.password_rotation.rotated_at == "2026-07-29T12:00:00+00:00"
        assert srv.password_rotation.acknowledged is False

    def test_password_rotation_failed_without_timestamp(self):
        srv = _server(password_rotation={"status": "failed", "rotated_at": None})
        assert srv.password_rotation.status == "failed"
        assert srv.password_rotation.rotated_at is None

    def test_password_rotation_null_is_none(self):
        assert _server(password_rotation=None).password_rotation is None

    def test_maintenance_reason(self):
        assert _server(maintenance_reason="Замена БП").maintenance_reason == "Замена БП"
        assert _server(maintenance_reason=None).maintenance_reason is None
        assert _server().maintenance_reason is None

    def test_queue_fields(self):
        srv = _server(queue_disabled=True, suggested_alternative=SUBSTITUTION)
        assert srv.queue_disabled is True
        assert srv.suggested_alternative.gpu_count == 1
        assert _server().queue_disabled is False
        assert _server().suggested_alternative is None


class TestOSImageCudaVersion:
    def test_cuda_version(self):
        img = OSImage.from_dict({"id": 1, "name": "Ubuntu 24.04", "cuda_version": "13.3"})
        assert img.cuda_version == "13.3"

    def test_cuda_version_absent_or_null(self):
        assert OSImage.from_dict({"id": 1, "name": "Windows"}).cuda_version is None
        assert OSImage.from_dict(
            {"id": 1, "name": "Windows", "cuda_version": None}
        ).cuda_version is None
