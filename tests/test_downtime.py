"""Unit tests for portal.downtime."""

import textwrap
from unittest.mock import MagicMock, patch

import arrow
import downtime as dt  # imported directly from portal/ via conftest.py sys.path
import pytest

WATCHED = next(iter(dt.WATCHED_RESOURCES))
OTHER = "MWT2_CE_UIUC"


def _fmt(a: arrow.Arrow) -> str:
    """Format an arrow datetime the way MWT2_downtime.yaml does."""
    return a.format("MMM D, YYYY HH:mm ZZ").replace("+00:00", "+0000")


def _yaml(entries: list[dict]) -> str:
    lines = []
    for e in entries:
        lines.append(
            textwrap.dedent(
                f"""\
            - Class: {e.get("Class", "SCHEDULED")}
              Description: {e.get("Description", "Maintenance")}
              EndTime: {e["EndTime"]}
              ID: {e.get("ID", 9999)}
              ResourceName: {e["ResourceName"]}
              Services:
              - Storage
              Severity: {e.get("Severity", "Outage")}
              StartTime: {e["StartTime"]}
            """
            )
        )
    return "\n".join(lines)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset module state between tests."""
    original = dict(dt._state)
    yield
    with dt._lock:
        dt._state.update(original)
        dt._state["active"] = []
        dt._state["upcoming"] = []
        dt._state["fetched_at"] = None
        dt._state["error"] = None


def _mock_get(yaml_text: str):
    resp = MagicMock()
    resp.text = yaml_text
    resp.raise_for_status = MagicMock()
    return resp


class TestRefresh:
    def test_active_entry_classified_correctly(self):
        now = arrow.utcnow()
        start = now.shift(hours=-1)
        end = now.shift(hours=+1)
        yaml_text = _yaml(
            [{"ResourceName": WATCHED, "StartTime": _fmt(start), "EndTime": _fmt(end)}]
        )
        with patch("downtime.requests.get", return_value=_mock_get(yaml_text)):
            dt.refresh()
        assert len(dt._state["active"]) == 1
        assert dt._state["upcoming"] == []

    def test_upcoming_entry_within_window(self):
        now = arrow.utcnow()
        start = now.shift(days=3)
        end = now.shift(days=4)
        yaml_text = _yaml(
            [{"ResourceName": WATCHED, "StartTime": _fmt(start), "EndTime": _fmt(end)}]
        )
        with patch("downtime.requests.get", return_value=_mock_get(yaml_text)):
            dt.refresh()
        assert dt._state["active"] == []
        assert len(dt._state["upcoming"]) == 1

    def test_upcoming_entry_beyond_window_excluded(self):
        now = arrow.utcnow()
        start = now.shift(days=10)
        end = now.shift(days=11)
        yaml_text = _yaml(
            [{"ResourceName": WATCHED, "StartTime": _fmt(start), "EndTime": _fmt(end)}]
        )
        with patch("downtime.requests.get", return_value=_mock_get(yaml_text)):
            dt.refresh()
        assert dt._state["active"] == []
        assert dt._state["upcoming"] == []

    def test_past_entry_excluded(self):
        now = arrow.utcnow()
        start = now.shift(hours=-3)
        end = now.shift(hours=-1)
        yaml_text = _yaml(
            [{"ResourceName": WATCHED, "StartTime": _fmt(start), "EndTime": _fmt(end)}]
        )
        with patch("downtime.requests.get", return_value=_mock_get(yaml_text)):
            dt.refresh()
        assert dt._state["active"] == []
        assert dt._state["upcoming"] == []

    def test_unwatched_resource_excluded(self):
        now = arrow.utcnow()
        start = now.shift(hours=-1)
        end = now.shift(hours=+1)
        yaml_text = _yaml(
            [{"ResourceName": OTHER, "StartTime": _fmt(start), "EndTime": _fmt(end)}]
        )
        with patch("downtime.requests.get", return_value=_mock_get(yaml_text)):
            dt.refresh()
        assert dt._state["active"] == []
        assert dt._state["upcoming"] == []

    def test_network_failure_preserves_previous_state(self):
        now = arrow.utcnow()
        start = now.shift(hours=-1)
        end = now.shift(hours=+1)
        yaml_text = _yaml(
            [{"ResourceName": WATCHED, "StartTime": _fmt(start), "EndTime": _fmt(end)}]
        )
        with patch("downtime.requests.get", return_value=_mock_get(yaml_text)):
            dt.refresh()
        assert len(dt._state["active"]) == 1

        with patch(
            "downtime.requests.get", side_effect=ConnectionError("network down")
        ):
            dt.refresh()

        assert len(dt._state["active"]) == 1
        assert dt._state["error"] is not None

    def test_multiple_entries_sorted_by_start_time(self):
        now = arrow.utcnow()
        entries = [
            {
                "ResourceName": WATCHED,
                "StartTime": _fmt(now.shift(days=5)),
                "EndTime": _fmt(now.shift(days=6)),
                "Description": "Later",
            },
            {
                "ResourceName": WATCHED,
                "StartTime": _fmt(now.shift(days=2)),
                "EndTime": _fmt(now.shift(days=3)),
                "Description": "Earlier",
            },
        ]
        yaml_text = _yaml(entries)
        with patch("downtime.requests.get", return_value=_mock_get(yaml_text)):
            dt.refresh()
        upcoming = dt._state["upcoming"]
        assert len(upcoming) == 2
        assert upcoming[0]["Description"] == "Earlier"
        assert upcoming[1]["Description"] == "Later"

    def test_get_downtimes_returns_snapshot(self):
        now = arrow.utcnow()
        start = now.shift(hours=-1)
        end = now.shift(hours=+1)
        yaml_text = _yaml(
            [{"ResourceName": WATCHED, "StartTime": _fmt(start), "EndTime": _fmt(end)}]
        )
        with patch("downtime.requests.get", return_value=_mock_get(yaml_text)):
            dt.refresh()
        result = dt.get_downtimes()
        assert isinstance(result, dict)
        assert "active" in result
        assert "upcoming" in result
        assert "fetched_at" in result
