"""Unit tests for portal.jupyterlab's Kubernetes client lifecycle."""

import datetime
import sys
import threading
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


class TestNotebookMaintenanceGuard:
    """start_notebook_maintenance() is called from @app.before_request, i.e.
    once per HTTP request. It must be idempotent so it starts the maintenance
    thread exactly once instead of leaking one infinite-loop thread per request
    (the request-amplified thread leak that OOM-killed the pod)."""

    def test_repeated_calls_start_exactly_one_daemon_thread(
        self, jupyterlab, monkeypatch
    ):
        jupyterlab._maintenance_started = False
        threads = []

        def fake_thread(*args, **kwargs):
            handle = MagicMock()
            threads.append((kwargs, handle))
            return handle

        monkeypatch.setattr(jupyterlab.threading, "Thread", fake_thread)

        for _ in range(50):
            jupyterlab.start_notebook_maintenance()

        assert len(threads) == 1
        # daemon so the never-terminating loop can't block process shutdown
        assert threads[0][0].get("daemon") is True
        threads[0][1].start.assert_called_once()

    def test_concurrent_calls_start_exactly_one_thread(self, jupyterlab, monkeypatch):
        """Two requests racing into the function must still start one thread;
        the lock makes the check-and-set atomic."""
        jupyterlab._maintenance_started = False
        real_thread_cls = threading.Thread  # capture before patching Thread
        started = []

        def fake_thread(*args, **kwargs):
            started.append(MagicMock())
            return started[-1]

        monkeypatch.setattr(jupyterlab.threading, "Thread", fake_thread)

        barrier = threading.Barrier(8)

        def worker():
            barrier.wait()
            jupyterlab.start_notebook_maintenance()

        racers = [real_thread_cls(target=worker) for _ in range(8)]
        for racer in racers:
            racer.start()
        for racer in racers:
            racer.join()

        assert len(started) == 1


class TestRunNotebookMaintenance:
    """run_notebook_maintenance() is the single-pass sweep shared by the
    in-process loop and the af-notebook-maintenance CronJob: it deletes only
    expired notebooks and returns (no infinite loop)."""

    def test_removes_only_expired_notebooks_in_one_pass(self, jupyterlab, monkeypatch):
        past = datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)
        future = datetime.datetime(2999, 1, 1, tzinfo=datetime.timezone.utc)

        expired = MagicMock()
        expired.metadata.name = "old-notebook"
        alive = MagicMock()
        alive.metadata.name = "fresh-notebook"
        no_ttl = MagicMock()
        no_ttl.metadata.name = "no-ttl-notebook"

        fake_api = MagicMock()
        fake_api.list_namespaced_pod.return_value.items = [expired, alive, no_ttl]
        monkeypatch.setattr(
            jupyterlab.client, "CoreV1Api", lambda api_client=None: fake_api
        )

        expirations = {id(expired): past, id(alive): future, id(no_ttl): None}
        monkeypatch.setattr(
            jupyterlab, "get_expiration_date", lambda pod: expirations[id(pod)]
        )

        removed = []
        monkeypatch.setattr(
            jupyterlab, "remove_notebook", lambda name: removed.append(name)
        )

        jupyterlab.run_notebook_maintenance()

        assert removed == ["old-notebook"]


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
