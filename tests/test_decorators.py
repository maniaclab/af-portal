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
    fake_connect_module.get_user_profile = MagicMock(return_value=None)
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
    app.config["DISABLED_SERVICES"] = frozenset()

    @app.route("/")
    def home():
        return "home"

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


class TestServiceEnabled:
    """Non-admins are turned away from a service listed in DISABLED_SERVICES.
    Greying out the navbar link is not enough because users can still type
    the URL, so the route itself must refuse the request."""

    @pytest.fixture
    def profile(self, decorators):
        """Return the connect.get_user_profile stub and reset it afterwards."""
        stub = sys.modules["portal.connect"].get_user_profile
        yield stub
        stub.reset_mock(return_value=True)
        stub.return_value = None

    def _call(self, decorators, flask_app, disabled):
        flask_app.config["DISABLED_SERVICES"] = frozenset(disabled)
        with flask_app.test_request_context("/jupyterlab"):
            flask.session["is_authenticated"] = True
            flask.session["unix_name"] = "jdoe"
            called = []

            @decorators.service_enabled("jupyterlab")
            def view():
                called.append(True)
                return "ok"

            response = view()
            return called, response, flask.get_flashed_messages(with_categories=True)

    @pytest.mark.parametrize("role", ["active", "admin"])
    def test_enabled_service_is_allowed(self, decorators, flask_app, profile, role):
        profile.return_value = {"role": role}
        called, response, flashes = self._call(decorators, flask_app, [])
        assert called == [True]
        assert response == "ok"
        assert flashes == []

    @pytest.mark.parametrize("role", ["active", "pending", "nonmember"])
    def test_disabled_service_rejects_non_admin(
        self, decorators, flask_app, profile, role
    ):
        profile.return_value = {"role": role}
        called, response, flashes = self._call(decorators, flask_app, ["jupyterlab"])
        assert called == []
        assert response.status_code == 302
        assert response.location == "/"
        assert flashes == [("warning", "JupyterLab is temporarily unavailable.")]

    def test_disabled_service_rejects_user_without_profile(
        self, decorators, flask_app, profile
    ):
        profile.return_value = None
        called, response, _ = self._call(decorators, flask_app, ["jupyterlab"])
        assert called == []
        assert response.status_code == 302

    def test_disabled_service_allows_admin(self, decorators, flask_app, profile):
        profile.return_value = {"role": "admin"}
        called, response, flashes = self._call(decorators, flask_app, ["jupyterlab"])
        assert called == [True]
        assert response == "ok"
        assert flashes == []
        profile.assert_called_once_with("jdoe")

    def test_other_disabled_service_does_not_block(
        self, decorators, flask_app, profile
    ):
        profile.return_value = {"role": "active"}
        called, _, _ = self._call(decorators, flask_app, ["reana"])
        assert called == [True]

    def test_unknown_service_key_fails_at_decoration(self, decorators):
        with pytest.raises(KeyError):
            decorators.service_enabled("not-a-service")
