"""Unit tests for portal.jupyterlab's Kubernetes client lifecycle."""

import sys
import types
from pathlib import Path
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
