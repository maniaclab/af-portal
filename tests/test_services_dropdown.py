"""Integration tests that render the real portal/templates/services_dropdown.html."""

from pathlib import Path

import flask
import pytest
import services  # imported directly from portal/ via conftest.py sys.path

TEMPLATES_DIR = Path(__file__).parent.parent / "portal" / "templates"


@pytest.fixture
def flask_app():
    app = flask.Flask(__name__, template_folder=str(TEMPLATES_DIR))
    app.secret_key = "test-secret"

    @app.route("/jupyterlab")
    def open_jupyterlab():
        return "jupyterlab"

    @app.route("/chat")
    def chat():
        return "chat"

    return app


def _render(flask_app, role, disabled):
    with flask_app.test_request_context("/"):
        flask.session["role"] = role
        return flask.render_template(
            "services_dropdown.html",
            services=services.SERVICES,
            disabled_services=frozenset(disabled),
        )


class TestServicesDropdown:
    @pytest.mark.parametrize("role", ["active", "admin"])
    def test_enabled_services_link_to_their_targets(self, flask_app, role):
        html = _render(flask_app, role, [])
        assert 'href="/jupyterlab"' in html
        assert 'href="/chat"' in html
        assert 'href="https://reana.af.uchicago.edu/"' in html
        assert "disabled" not in html

    def test_only_internal_jupyterlab_stays_in_same_tab(self, flask_app):
        html = _render(flask_app, "active", [])
        assert html.count('target="_blank"') == len(services.SERVICES) - 1

    def test_disabled_services_are_greyed_out_for_non_admin(self, flask_app):
        html = _render(flask_app, "active", ["jupyterlab", "reana"])
        assert 'href="/jupyterlab"' not in html
        assert "reana.af.uchicago.edu" not in html
        assert html.count('aria-disabled="true"') == 2
        assert "JupyterLab (unavailable)" in html
        assert "REANA (unavailable)" in html
        # Services that are not disabled keep their links.
        assert 'href="/chat"' in html

    def test_disabled_services_stay_usable_for_admin(self, flask_app):
        html = _render(flask_app, "admin", ["jupyterlab"])
        assert 'href="/jupyterlab"' in html
        assert 'aria-disabled="true"' not in html
        assert "Disabled for users" in html
