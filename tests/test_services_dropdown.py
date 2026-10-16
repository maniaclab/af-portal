"""Tests for the Services dropdown and the BinderHub promotion / JupyterLab
deprecation in templates. The dropdown tests render the real
portal/templates/services_dropdown.html."""

import re
from pathlib import Path

import flask
import pytest
import services  # imported directly from portal/ via conftest.py sys.path

TEMPLATES_DIR = Path(__file__).parent.parent / "portal" / "templates"
BINDERHUB_URL = "https://binderhub.af.uchicago.edu/"


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


def _labels(html) -> list[str]:
    """Return the visible label of each Services dropdown item, in order."""
    labels = re.findall(r'class="dropdown-item[^"]*"[^>]*>(.*?)</a', html, re.DOTALL)
    return [" ".join(re.sub(r"<[^>]+>", "", label).split()) for label in labels]


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


class TestServicesDropdownDeprecation:
    @pytest.fixture
    def services_items(self, flask_app) -> list[str]:
        return _labels(_render(flask_app, "active", []))

    def test_binderhub_listed_first(self, services_items):
        assert services_items[0] == "BinderHub"

    def test_jupyterlab_listed_last(self, services_items):
        assert "JupyterLab" in services_items[-1]

    def test_jupyterlab_marked_deprecated(self, services_items):
        assert "deprecated Dec 1st" in services_items[-1]

    def test_jupyterlab_marked_deprecated_when_disabled(self, flask_app):
        labels = _labels(_render(flask_app, "active", ["jupyterlab"]))
        assert "deprecated Dec 1st" in labels[-1]


class TestJupyterLabDeprecationBanner:
    @pytest.fixture(scope="class")
    def html(self) -> str:
        return (TEMPLATES_DIR / "jupyterlab.html").read_text()

    def test_banner_present(self, html):
        assert 'class="alert alert-warning"' in html
        assert "December 1st" in html

    def test_banner_links_to_binderhub(self, html):
        assert f'href="{BINDERHUB_URL}"' in html


class TestNotebooksUserEmptyState:
    @pytest.fixture(scope="class")
    def html(self) -> str:
        return (TEMPLATES_DIR / "notebooks_user.html").read_text()

    def test_points_to_binderhub(self, html):
        assert f'href="{BINDERHUB_URL}"' in html

    def test_no_longer_points_to_jupyterlab(self, html):
        assert "url_for('open_jupyterlab')" not in html
