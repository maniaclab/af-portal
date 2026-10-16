"""Unit tests for the Services dropdown in portal/templates/base.html."""

import re
from pathlib import Path

import pytest

BASE_HTML = Path(__file__).parent.parent / "portal" / "templates" / "base.html"


@pytest.fixture(scope="module")
def services_items() -> list[str]:
    """Return the visible label of each Services dropdown item, in order."""
    html = BASE_HTML.read_text()
    menu = html.split("Services", 1)[1].split("</ul>", 1)[0]
    labels = re.findall(r'class="dropdown-item"[^>]*>(.*?)</a', menu, re.DOTALL)
    return [" ".join(label.split()) for label in labels]


class TestServicesDropdown:
    def test_binderhub_listed_first(self, services_items):
        assert services_items[0] == "BinderHub"

    def test_jupyterlab_listed_after_binderhub(self, services_items):
        jlab = next(i for i, s in enumerate(services_items) if "JupyterLab" in s)
        assert jlab > services_items.index("BinderHub")

    def test_jupyterlab_marked_deprecated(self, services_items):
        jlab = next(s for s in services_items if "JupyterLab" in s)
        assert "deprecated Dec 1st" in jlab
