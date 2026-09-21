"""Unit tests for the validate_notebook decorator in portal/decorators.py."""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import flask
import pytest

PORTAL_DIR = Path(__file__).parent.parent / "portal"


def _install_fake_portal_package():
    """Stub portal/portal.app/portal.connect/portal.jupyterlab so
    portal.decorators can be imported without a real portal.conf, Flask app,
    or Kubernetes client (mirrors the bypass test_jupyterlab.py uses)."""
    fake_portal = types.ModuleType("portal")
    fake_portal.__path__ = [str(PORTAL_DIR)]
    sys.modules.setdefault("portal", fake_portal)

    fake_app_module = types.ModuleType("portal.app")
    fake_app_module.app = MagicMock()
    fake_app_module.logger = MagicMock()
    sys.modules["portal.app"] = fake_app_module

    fake_connect_module = types.ModuleType("portal.connect")
    sys.modules["portal.connect"] = fake_connect_module

    fake_jupyterlab_module = types.ModuleType("portal.jupyterlab")
    fake_jupyterlab_module.MAX_LIFETIME_HOURS = 72
    fake_jupyterlab_module.notebook_name_available = MagicMock(return_value=True)
    fake_jupyterlab_module.supported_images = MagicMock(return_value=["test-image"])
    fake_jupyterlab_module.get_gpu_availability = MagicMock(return_value=[])
    sys.modules["portal.jupyterlab"] = fake_jupyterlab_module


@pytest.fixture(scope="module")
def decorators():
    """Stubs portal.app/connect/jupyterlab in sys.modules just long enough to
    import portal.decorators, then restores whatever was there before so
    other test files (e.g. test_jupyterlab.py) still import the real
    portal.jupyterlab instead of this module's fakes."""
    stubbed_keys = ["portal", "portal.app", "portal.connect", "portal.jupyterlab"]
    saved = {key: sys.modules.get(key) for key in stubbed_keys}

    _install_fake_portal_package()
    import portal.decorators as decorators_module

    yield decorators_module

    for key, module in saved.items():
        if module is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = module
    sys.modules.pop("portal.decorators", None)


@pytest.fixture
def flask_app():
    app = flask.Flask(__name__)
    app.secret_key = "test-secret"

    @app.route("/jupyterlab/configure")
    def configure_notebook():
        return "configure"

    return app


def _form_data(**overrides):
    data = {
        "notebook-name": "test-notebook",
        "image": "test-image",
        "cpu": "1",
        "memory": "1",
        "gpu": "0",
        "gpu-product": "",
        "duration": "8",
    }
    data.update(overrides)
    return data


class TestValidateNotebookDuration:
    """The 'duration' (hours) form field must be bounds-checked server-side,
    the same way cpu/memory/gpu already are: the HTML form's max="72" is a
    browser-only constraint and does nothing to stop a direct POST."""

    @pytest.mark.parametrize("duration", ["0", "-5", "73", "999999"])
    def test_out_of_bounds_duration_is_rejected(self, decorators, flask_app, duration):
        with flask_app.test_request_context(
            "/jupyterlab/deploy", method="POST", data=_form_data(duration=duration)
        ):
            called = []

            @decorators.validate_notebook
            def view():
                called.append(True)
                return "ok"

            response = view()

            assert called == []
            assert response.status_code == 302

    @pytest.mark.parametrize("duration", ["1", "8", "72"])
    def test_in_bounds_duration_is_accepted(self, decorators, flask_app, duration):
        with flask_app.test_request_context(
            "/jupyterlab/deploy", method="POST", data=_form_data(duration=duration)
        ):
            called = []

            @decorators.validate_notebook
            def view():
                called.append(True)
                return "ok"

            view()

            assert called == [True]
