"""CronJob entrypoint: run one notebook-maintenance sweep, then exit.

Invoked by the ``af-notebook-maintenance`` Kubernetes CronJob as
``python -m portal.notebook_maintenance``. This replaces the in-process
``jupyterlab.start_notebook_maintenance`` thread, which stays in place as a
fallback until the CronJob is confirmed running in production.

NOTE: importing ``portal.jupyterlab`` pulls in ``portal/__init__`` (the full
Flask app plus ``downtime.start_scheduler`` and the email worker). That is
harmless for this short-lived process -- those are daemon threads that do not
block exit -- but it does trigger one spurious downtime refresh per run. If we
want to avoid that, gate the web-only startup (scheduler + worker) behind an
"am I the web server" check in ``portal.app``/``portal.views`` as a follow-up.
"""

from portal import jupyterlab

if __name__ == "__main__":
    jupyterlab.run_notebook_maintenance()
