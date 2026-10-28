"""
Registry of the services listed in the navbar's Services dropdown.

Any service can be disabled for non-admin users by listing its key in the
DISABLED_SERVICES config value. In deployment this is set through the
FLASK_DISABLED_SERVICES environment variable as a JSON list, for example
FLASK_DISABLED_SERVICES='["jupyterlab", "reana"]'. Admins keep full access so
they can still check that a disabled service works.

For services hosted outside the portal, the portal can only disable the link.
It has no way to block requests to the external host.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Service:
    key: str
    label: str
    # Exactly one of endpoint (a portal view function) or url (an external site) is set.
    endpoint: str | None = None
    url: str | None = None
    new_tab: bool = True


SERVICES = (
    Service("jupyterlab", "JupyterLab", endpoint="open_jupyterlab", new_tab=False),
    Service("coffea-casa", "Coffea Casa", url="https://coffea.af.uchicago.edu/"),
    Service("binderhub", "BinderHub", url="https://binderhub.af.uchicago.edu/"),
    Service("servicex", "ServiceX", url="https://servicex.af.uchicago.edu"),
    Service("assistant", "Assistant", endpoint="chat"),
    Service("mcp-portal", "MCP Portal", url="https://mcp-portal.af.uchicago.edu/"),
    Service("reana", "REANA", url="https://reana.af.uchicago.edu/"),
)

_SERVICES_BY_KEY = {service.key: service for service in SERVICES}


def get(key: str) -> Service:
    """Return the service registered under key. Raises KeyError if the key is unknown."""
    return _SERVICES_BY_KEY[key]


def parse_disabled_services(value) -> frozenset[str]:
    """Check the DISABLED_SERVICES config value and return it as a frozenset.

    Bad values raise an error at startup instead of being ignored. Otherwise a
    typo in the env var would leave a service enabled that was meant to be off.
    """
    if not isinstance(value, list) or not all(isinstance(key, str) for key in value):
        msg = f"DISABLED_SERVICES must be a list of service keys, got {value!r}"
        raise ValueError(msg)
    unknown = sorted(set(value) - _SERVICES_BY_KEY.keys())
    if unknown:
        msg = f"Unknown service keys in DISABLED_SERVICES: {unknown}. Valid keys: {sorted(_SERVICES_BY_KEY)}"
        raise ValueError(msg)
    return frozenset(value)
