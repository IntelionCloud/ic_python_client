"""Tests for flavor resource."""

import respx

from intelion_cloud import IntelionCloud

from .conftest import API_URL, BASE_URL, SAMPLE_FLAVOR


class TestFlavors:
    @respx.mock(base_url=API_URL)
    def test_list(self, respx_mock):
        respx_mock.get("flavors/").respond(
            200,
            json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [SAMPLE_FLAVOR],
            },
        )
        client = IntelionCloud(token="tok", base_url=BASE_URL)
        flavors = client.flavors.list()
        assert len(flavors) == 1
        f = flavors[0]
        assert f.id == "abc-def-123"
        assert f.name == "1x H100 80GB"
        assert f.gpu_count == 1
        assert f.gpu is not None
        assert f.gpu.name == "NVIDIA H100"
        assert f.cpu is not None
        assert f.cpu.cores == 48
        client.close()
