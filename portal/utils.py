from flask import request
from threading import Lock

import globus_sdk

try:
    import ConfigParser as configparser
except:
    import configparser as configparser

try:
    from urllib.parse import urlparse, urljoin
except ImportError:
    from urlparse import urlparse, urljoin

from portal import app
from portal.connect_api import domain_name_edgecase

brand_dir = app.config["MARKDOWN_DIR"]


def flash_message_parser(route_name):

    # domain_name = request.headers['Host']
    # if 'usatlas' in domain_name:
    #     domain_name = 'atlas.ci-connect.net'
    # elif 'uscms' in domain_name:
    #     domain_name = 'cms.ci-connect.net'
    # elif 'uchicago' in domain_name:
    #     domain_name = 'psdconnect.uchicago.edu'
    # elif 'snowmass21' in domain_name:
    #     domain_name = 'snowmass21.ci-connect.net'

    domain_name = domain_name_edgecase()
    # print(domain_name)
    config = configparser.RawConfigParser(allow_no_value=True)
    config.read(brand_dir + "/" + domain_name + "/flash_messages/flash_messages.cfg")
    flash_message = config.get("flash_messages", route_name)
    return flash_message


def load_portal_client():
    """Create an AuthClient for the portal"""
    return globus_sdk.ConfidentialAppAuthClient(
        app.config["PORTAL_CLIENT_ID"], app.config["PORTAL_CLIENT_SECRET"]
    )


def is_safe_redirect_url(target):
    """https://security.openstack.org/guidelines/dg_avoid-unvalidated-redirects.html"""  # noqa
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))

    return (
        redirect_url.scheme in ("http", "https")
        and host_url.netloc == redirect_url.netloc
    )


def get_safe_redirect():
    """https://security.openstack.org/guidelines/dg_avoid-unvalidated-redirects.html"""  # noqa
    url = request.args.get("next")
    if url and is_safe_redirect_url(url):
        return url

    url = request.referrer
    if url and is_safe_redirect_url(url):
        return url

    return "/"


def get_portal_tokens(
    scopes=["openid", "urn:globus:auth:scope:demo-resource-server:all"]
):
    """
    Uses the client_credentials grant to get access tokens on the
    Portal's "client identity."
    """
    with get_portal_tokens.lock:
        if not get_portal_tokens.access_tokens:
            get_portal_tokens.access_tokens = {}

        scope_string = " ".join(scopes)

        client = load_portal_client()
        tokens = client.oauth2_client_credentials_tokens(requested_scopes=scope_string)

        # walk all resource servers in the token response (includes the
        # top-level server, as found in tokens.resource_server), and store the
        # relevant Access Tokens
        for resource_server, token_info in tokens.by_resource_server.items():
            get_portal_tokens.access_tokens.update(
                {
                    resource_server: {
                        "token": token_info["access_token"],
                        "scope": token_info["scope"],
                        "expires_at": token_info["expires_at_seconds"],
                    }
                }
            )

        return get_portal_tokens.access_tokens


get_portal_tokens.lock = Lock()
get_portal_tokens.access_tokens = None
