"""Hardware catalog resources: gpus / cpus / ram / ssds / software-addons."""

import httpx
import respx

from intelion_cloud import IntelionCloud, SoftwareAddon

from .conftest import API_URL, BASE_URL, SAMPLE_CPU, SAMPLE_GPU, SAMPLE_RAM, SAMPLE_SSD

SAMPLE_ADDON = {
    "id": 3,
    "slug": "comfyui",
    "name": "ComfyUI",
    "description": "Node-based Stable Diffusion UI",
    "port": 8188,
    "compatible_os_ids": [1, 2],
    "compatible_gpu_ids": [],
    "requires_gpu": True,
}


def _page(results, next_url=None):
    return {"count": len(results), "next": next_url, "previous": None, "results": results}


class TestCatalogLists:
    @respx.mock(base_url=API_URL)
    def test_gpus_list(self, respx_mock):
        respx_mock.get("gpus/").respond(200, json=_page([SAMPLE_GPU]))
        client = IntelionCloud(token="tok", base_url=BASE_URL)

        gpus = client.gpus.list()

        assert len(gpus) == 1
        assert gpus[0].slug == "nvidia-h100"

    @respx.mock(base_url=API_URL)
    def test_cpus_ram_ssds_lists(self, respx_mock):
        respx_mock.get("cpus/").respond(200, json=_page([SAMPLE_CPU]))
        respx_mock.get("ram/").respond(200, json=_page([SAMPLE_RAM]))
        respx_mock.get("ssds/").respond(200, json=_page([SAMPLE_SSD]))
        client = IntelionCloud(token="tok", base_url=BASE_URL)

        assert len(client.cpus.list()) == 1
        assert len(client.ram.list()) == 1
        assert len(client.ssds.list()) == 1

    @respx.mock(base_url=API_URL)
    def test_gpu_get_by_id(self, respx_mock):
        respx_mock.get("gpus/1/").respond(200, json=SAMPLE_GPU)
        client = IntelionCloud(token="tok", base_url=BASE_URL)

        assert client.gpus.get(1).name == "NVIDIA H100"

    @respx.mock(base_url=API_URL)
    def test_gpus_single_page(self, respx_mock):
        respx_mock.get("gpus/").respond(
            200, json={"count": 9, "next": "https://x/api/v2/gpus/?page=2",
                       "previous": None, "results": [SAMPLE_GPU]}
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)

        page = client.gpus.list(page=1)

        assert page.count == 9
        assert page.has_next is True

    @respx.mock(base_url=API_URL)
    def test_gpus_auto_pagination_follows_next(self, respx_mock):
        respx_mock.get("gpus/").mock(side_effect=[
            httpx.Response(200, json={
                "count": 2, "next": "https://intelion.cloud/api/v2/gpus/?page=2",
                "previous": None, "results": [SAMPLE_GPU],
            }),
            httpx.Response(200, json=_page([{**SAMPLE_GPU, "id": 2, "slug": "nvidia-a100"}])),
        ])
        client = IntelionCloud(token="tok", base_url=BASE_URL)

        gpus = client.gpus.list()

        assert [g.slug for g in gpus] == ["nvidia-h100", "nvidia-a100"]


class TestSoftwareAddons:
    def test_model_from_dict(self):
        addon = SoftwareAddon.from_dict(SAMPLE_ADDON)
        assert addon.slug == "comfyui"
        assert addon.port == 8188
        assert addon.requires_gpu is True
        assert addon.compatible_gpu_ids == []

    def test_model_tolerates_missing_optional_fields(self):
        addon = SoftwareAddon.from_dict({"id": 1, "slug": "x", "name": "X"})
        assert addon.description == ""
        assert addon.port is None
        assert addon.requires_gpu is False

    @respx.mock(base_url=API_URL)
    def test_list(self, respx_mock):
        respx_mock.get("software-addons/").respond(200, json=_page([SAMPLE_ADDON]))
        client = IntelionCloud(token="tok", base_url=BASE_URL)

        addons = client.software_addons.list()

        assert len(addons) == 1
        assert addons[0].name == "ComfyUI"

    @respx.mock(base_url=API_URL)
    def test_list_follows_limit_offset_next(self, respx_mock):
        """Аддоны пагинируются limit/offset, а не page — auto-paginate обязан
        идти по URL из `next`, а не подставлять ?page=N."""
        respx_mock.get("software-addons/").mock(side_effect=[
            httpx.Response(200, json={
                "count": 2,
                "next": "https://intelion.cloud/api/v2/software-addons/?limit=1&offset=1",
                "previous": None,
                "results": [SAMPLE_ADDON],
            }),
            httpx.Response(200, json=_page([{**SAMPLE_ADDON, "id": 4, "slug": "openclaw"}])),
        ])
        client = IntelionCloud(token="tok", base_url=BASE_URL)

        addons = client.software_addons.list()

        assert [a.slug for a in addons] == ["comfyui", "openclaw"]
        assert dict(addons and respx_mock.calls[1].request.url.params) == {
            "limit": "1",
            "offset": "1",
        }

    def test_no_page_argument(self):
        """page= у аддонов нет намеренно: DRF LimitOffsetPagination молча его
        игнорирует и вернул бы первую страницу под видом N-й."""
        import inspect

        from intelion_cloud.resources.catalog import SoftwareAddons

        assert "page" not in inspect.signature(SoftwareAddons.list).parameters
