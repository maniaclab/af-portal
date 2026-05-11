"""
Fetch and cache MWT2 downtime entries from the OSG topology repo.

Refresh runs once at startup and every 24 h via a background APScheduler job.
Requests never pay the GitHub round-trip cost.
"""

import atexit
import logging
import threading
from datetime import timedelta

import arrow
import requests
import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

DOWNTIME_URL = (
    "https://raw.githubusercontent.com/opensciencegrid/topology/master"
    "/topology/University%20of%20Chicago/MWT2%20ATLAS%20UC/MWT2_downtime.yaml"
)
WATCHED_RESOURCES = frozenset({"MWT2_UC_XRootD_door", "MWT2_UC_WebDAV"})
UPCOMING_WINDOW = timedelta(days=7)
REFRESH_HOURS = 24

_lock = threading.Lock()
_state: dict = {"active": [], "upcoming": [], "fetched_at": None, "error": None}
_started = False


def _parse_entry(entry: dict, now: arrow.Arrow) -> dict | None:
    """Return the entry with parsed arrow datetimes, or None if unparsable."""
    try:
        start = arrow.get(entry["StartTime"], "MMM D, YYYY HH:mm Z")
        end = arrow.get(entry["EndTime"], "MMM D, YYYY HH:mm Z")
    except Exception:
        logger.warning("Could not parse downtime entry times: %s", entry.get("ID"))
        return None
    return {**entry, "StartTime": start, "EndTime": end}


def refresh() -> None:
    """Fetch the downtime YAML and update the cached state."""
    try:
        response = requests.get(DOWNTIME_URL, timeout=15)
        response.raise_for_status()
        entries = yaml.safe_load(response.text)
    except Exception as exc:
        logger.error("Failed to fetch MWT2 downtime: %s", exc)
        with _lock:
            _state["error"] = str(exc)
            _state["fetched_at"] = arrow.utcnow()
        return

    now = arrow.utcnow()
    upcoming_cutoff = now.shift(days=7)

    active = []
    upcoming = []
    for raw in entries:
        if raw.get("ResourceName") not in WATCHED_RESOURCES:
            continue
        entry = _parse_entry(raw, now)
        if entry is None:
            continue
        start, end = entry["StartTime"], entry["EndTime"]
        if end <= now:
            continue
        if start <= now:
            active.append(entry)
        elif start <= upcoming_cutoff:
            upcoming.append(entry)

    active.sort(key=lambda e: e["StartTime"])
    upcoming.sort(key=lambda e: e["StartTime"])

    with _lock:
        _state["active"] = active
        _state["upcoming"] = upcoming
        _state["fetched_at"] = now
        _state["error"] = None

    logger.info(
        "MWT2 downtime refreshed: %d active, %d upcoming", len(active), len(upcoming)
    )


def get_downtimes() -> dict:
    """Return a snapshot of the current downtime state for templates."""
    with _lock:
        return dict(_state)


def start_scheduler(app) -> None:
    # NOTE: safe with gunicorn --workers=1. If workers are ever scaled above 1,
    # each worker starts its own scheduler and fetches independently N× per day.
    # Revisit then: use a K8s CronJob + shared volume, or an external cache.
    global _started
    if _started:
        return
    _started = True

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        refresh,
        IntervalTrigger(hours=REFRESH_HOURS),
        next_run_time=arrow.utcnow().datetime,
        id="mwt2_downtime_refresh",
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))
    logger.info("MWT2 downtime scheduler started (interval=%dh)", REFRESH_HOURS)
