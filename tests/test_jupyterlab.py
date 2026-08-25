"""Unit tests for portal.jupyterlab's Kubernetes client lifecycle."""

import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

PORTAL_DIR = Path(__file__).parent.parent / "portal"


def _install_fake_portal_app():
    """Stub portal/portal.app so portal.jupyterlab can be imported without a
    real portal.conf or Flask app (mirrors the bypass conftest.py uses for
    portal.downtime, but jupyterlab imports portal.app directly)."""
    fake_portal = types.ModuleType("portal")
    fake_portal.__path__ = [str(PORTAL_DIR)]
    sys.modules.setdefault("portal", fake_portal)

    fake_app_module = types.ModuleType("portal.app")
    fake_app = MagicMock()
    fake_app.config = {"NAMESPACE": "af-jupyter"}
    fake_app_module.app = fake_app
    fake_app_module.logger = MagicMock()
    sys.modules["portal.app"] = fake_app_module


@pytest.fixture(scope="module")
def jupyterlab():
    _install_fake_portal_app()
    with patch("kubernetes.config.load_kube_config"):
        import portal.jupyterlab as jupyterlab_module
    return jupyterlab_module


class TestSharedApiClient:
    def test_corev1api_calls_reuse_the_same_api_client(self, jupyterlab, monkeypatch):
        """Every client.CoreV1Api() call site should share one ApiClient
        instead of constructing (and leaking) a new one per call."""
        seen_api_clients = []

        def fake_corev1api(api_client=None):
            seen_api_clients.append(api_client)
            mock_api = MagicMock()
            mock_api.list_namespaced_pod.return_value.items = []
            return mock_api

        monkeypatch.setattr(jupyterlab.client, "CoreV1Api", fake_corev1api)

        jupyterlab.list_notebooks()
        jupyterlab.notebook_name_available("some-notebook")

        assert len(seen_api_clients) == 2
        assert seen_api_clients[0] is not None
        assert seen_api_clients[0] is seen_api_clients[1]


def _make_node(
    name,
    product="NVIDIA-GeForce-RTX-2080-Ti",
    gpu_count=2,
    gpu_memory_mib=11264,
    allocatable_memory="10Gi",
    allocatable_cpu="4",
    unschedulable=False,
    taints=None,
):
    """Build a fake V1Node with just the fields get_gpu_availability reads.

    capacity is set equal to allocatable by default, since real nodes only
    differ by the small system/kube-reserved slice; tests that need to prove
    allocatable (not capacity) is used override capacity explicitly.
    """
    resources = {
        "nvidia.com/gpu": str(gpu_count),
        "memory": allocatable_memory,
        "cpu": allocatable_cpu,
    }
    return SimpleNamespace(
        metadata=SimpleNamespace(
            name=name,
            labels={
                "nvidia.com/gpu.product": product,
                "nvidia.com/gpu.memory": str(gpu_memory_mib),
                "nvidia.com/gpu.count": str(gpu_count),
            },
        ),
        spec=SimpleNamespace(unschedulable=unschedulable, taints=taints),
        status=SimpleNamespace(capacity=dict(resources), allocatable=dict(resources)),
    )


def _make_pod(gpu_request=0, memory_request=None, cpu_request=None):
    requests = {}
    if gpu_request:
        requests["nvidia.com/gpu"] = str(gpu_request)
    if memory_request:
        requests["memory"] = memory_request
    if cpu_request:
        requests["cpu"] = cpu_request
    container = SimpleNamespace(resources=SimpleNamespace(requests=requests))
    return SimpleNamespace(spec=SimpleNamespace(containers=[container]))


def _fake_api(nodes, pods_by_node):
    api = MagicMock()
    api.list_node.return_value = SimpleNamespace(items=nodes)

    def list_pods(field_selector=None, **kwargs):
        node_name = field_selector.split(",")[0].split("=", 1)[1]
        return SimpleNamespace(items=pods_by_node.get(node_name, []))

    api.list_pod_for_all_namespaces.side_effect = list_pods
    return api


class TestGpuAvailability:
    """dajiang-nn (af-jupyter) sat Pending indefinitely because the portal's
    pre-submission check (decorators.py) trusted get_gpu_availability, which
    counted a cordoned node's full, untouched capacity as free headroom."""

    def test_excludes_cordoned_node_from_availability(self, jupyterlab, monkeypatch):
        schedulable = _make_node("g003", allocatable_memory="10Gi", allocatable_cpu="4")
        cordoned = _make_node(
            "g007",
            allocatable_memory="10Gi",
            allocatable_cpu="4",
            unschedulable=True,
            taints=[
                SimpleNamespace(
                    key="node.kubernetes.io/unschedulable", effect="NoSchedule"
                )
            ],
        )
        pods_by_node = {
            "g003": [_make_pod(gpu_request=1, memory_request="8Gi", cpu_request="1")],
            "g007": [],
        }
        api = _fake_api([schedulable, cordoned], pods_by_node)
        monkeypatch.setattr(jupyterlab.client, "CoreV1Api", lambda api_client=None: api)

        result = jupyterlab.get_gpu_availability(product="NVIDIA-GeForce-RTX-2080-Ti")

        gpu = result[0]
        assert gpu["count"] == 2  # only g003's instances; g007 excluded entirely
        assert gpu["available"] == 1  # 2 - 1 requested, on g003 alone
        assert (
            gpu["mem_request_max"] == 2
        )  # g003's headroom (10Gi-8Gi); not g007's idle 10Gi
        assert gpu["cpu_request_max"] == 3

    def test_uses_allocatable_not_capacity_for_headroom(self, jupyterlab, monkeypatch):
        node = _make_node("g003", allocatable_memory="8Gi", allocatable_cpu="4")
        # Every real node's capacity exceeds its allocatable by the
        # kubelet/system-reserved slice; headroom must be computed against
        # allocatable, the actual schedulable ceiling.
        node.status.capacity["memory"] = "10Gi"
        node.status.capacity["cpu"] = "6"
        api = _fake_api([node], {"g003": []})
        monkeypatch.setattr(jupyterlab.client, "CoreV1Api", lambda api_client=None: api)

        result = jupyterlab.get_gpu_availability(product="NVIDIA-GeForce-RTX-2080-Ti")

        gpu = result[0]
        assert gpu["mem_request_max"] == 8
        assert gpu["cpu_request_max"] == 4
