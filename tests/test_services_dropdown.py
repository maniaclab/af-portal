"""Unit tests for the BinderHub promotion / JupyterLab deprecation in templates."""

import re
from pathlib import Path

import pytest

TEMPLATES = Path(__file__).parent.parent / "portal" / "templates"
BINDERHUB_URL = "https://binderhub.af.uchicago.edu/"


@pytest.fixture(scope="module")
def services_items() -> list[str]:
    """Return the visible label of each Services dropdown item, in order."""
    html = (TEMPLATES / "base.html").read_text()
    menu = html.split("Services", 1)[1].split("</ul>", 1)[0]
    labels = re.findall(r'class="dropdown-item"[^>]*>(.*?)</a', menu, re.DOTALL)
    return [" ".join(re.sub(r"<[^>]+>", "", label).split()) for label in labels]


class TestServicesDropdown:
    def test_binderhub_listed_first(self, services_items):
        assert services_items[0] == "BinderHub"

    def test_jupyterlab_listed_last(self, services_items):
        assert "JupyterLab" in services_items[-1]

    def test_jupyterlab_marked_deprecated(self, services_items):
        assert "deprecated Dec 1st" in services_items[-1]


class TestJupyterLabDeprecationBanner:
    @pytest.fixture(scope="class")
    def html(self) -> str:
        return (TEMPLATES / "jupyterlab.html").read_text()

    def test_banner_present(self, html):
        assert 'class="alert alert-warning"' in html
        assert "December 1st" in html

    def test_banner_links_to_binderhub(self, html):
        assert f'href="{BINDERHUB_URL}"' in html


class TestNotebooksUserEmptyState:
    @pytest.fixture(scope="class")
    def html(self) -> str:
        return (TEMPLATES / "notebooks_user.html").read_text()

    def test_points_to_binderhub(self, html):
        assert f'href="{BINDERHUB_URL}"' in html

    def test_no_longer_points_to_jupyterlab(self, html):
        assert "url_for('open_jupyterlab')" not in html
