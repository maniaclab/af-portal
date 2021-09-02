from flask import session, request
from portal import app
import requests
import json

# Read configurable tokens and endpoints from config file, values must be set
ciconnect_api_token = app.config["CONNECT_API_TOKEN"]
ciconnect_api_endpoint = app.config["CONNECT_API_ENDPOINT"]

try:
    user_access_token = get_user_access_token(session)
    query = {"token": user_access_token}
except:
    query = {"token": ciconnect_api_token}


def connect_name(group_name):
    """
    Returns string of root connect name, i.e. cms, osg, atlas, spt, etc.
    :param group_name: unix string name of group
    :return: string of connect name
    """
    connect_name = ".".join(group_name.split(".")[:2])
    return connect_name


def query_status_code(query_response):
    if query_response.status_code == requests.codes.ok:
        query_return = query_response.json()["items"]
    else:
        query_return = []
    return query_return


def get_multiplex(json):
    """
    Returns list of objects, containing multiplex information
    :param json: json object containing query and request methods
    :return: [{state, name, state_set_by}]
    """
    multiplex = requests.post(
        ciconnect_api_endpoint + "/v1alpha1/multiplex", params=query, json=json
    )
    multiplex = multiplex.json()
    return multiplex


#############################
#####       USER       ######
#############################


def get_user_info(session):
    """
    Returns object of user information
    :param session: user session to pull primary_identity
    :return: object {kind: User, apiVersion: v1alpha1, metadata: {access_token, unix_name}}
    """
    query = {"token": ciconnect_api_token, "globus_id": session["primary_identity"]}

    user = requests.get(ciconnect_api_endpoint + "/v1alpha1/find_user", params=query)
    user = user.json()
    return user


def get_user_group_memberships(session, unix_name):
    """
    Returns list of objects, containing group membership information
    :param session: user session to pull primary_identity
    :return: {query: {status: response, body: { apiVersion, kind, metadata: {} } }}
    """
    query = {"token": ciconnect_api_token, "globus_id": session["primary_identity"]}

    users_group_memberships = requests.get(
        ciconnect_api_endpoint + "/v1alpha1/users/" + unix_name + "/groups",
        params=query,
    )
    users_group_memberships = users_group_memberships.json()["group_memberships"]
    return users_group_memberships


def get_user_group_status(unix_name, group_name, session):
    """
    Returns user's status in specific group
    :param unix_name: string unix name of user
    :group_name: string name of group
    :param session: user session to pull primary_identity
    :return: string
    """
    query = {"token": ciconnect_api_token, "globus_id": session["primary_identity"]}

    user_status = requests.get(
        ciconnect_api_endpoint
        + "/v1alpha1/groups/"
        + group_name
        + "/members/"
        + unix_name,
        params=query,
    )
    user_status = user_status.json()["membership"]["state"]

    return user_status


def get_user_pending_project_requests(unix_name):
    """
    Returns user's status in root connect group
    :param unix_name: string user's unix name
    :param connect_group: string name of connect group
    :return: string (active, admin, nonmember)
    """
    query = {"token": ciconnect_api_token}
    pending_project_requests = requests.get(
        ciconnect_api_endpoint + "/v1alpha1/users/" + unix_name + "/group_requests",
        params=query,
    )
    pending_project_requests = pending_project_requests.json()["groups"]
    return pending_project_requests


def get_user_connect_status(unix_name, connect_group):
    """
    Returns user's status in root connect group
    :param unix_name: string user's unix name
    :param connect_group: string name of connect group
    :return: string (active, admin, nonmember)
    """
    connect_status = requests.get(
        ciconnect_api_endpoint
        + "/v1alpha1/users/"
        + unix_name
        + "/groups/"
        + connect_group,
        params=query,
    )
    connect_status = connect_status.json()["membership"]["state"]
    return connect_status


def get_enclosing_group_status(group_name, unix_name):
    enclosing_group_name = ".".join(group_name.split(".")[:-1])
    if enclosing_group_name:
        enclosing_status = get_user_connect_status(unix_name, enclosing_group_name)
    else:
        enclosing_status = None
    return enclosing_status


def enclosing_admin_status(session, group_name):
    group_split = group_name.split(".")
    admin = False
    enclosing_group = group_split[0]

    while group_split and not admin:
        enclosing_group += ".{}".format(group_split.pop(0))
        if get_user_connect_status(session["unix_name"], enclosing_group) == "admin":
            admin = True
        else:
            enclosing_group
    return admin


#############################
#####       GROUP      ######
#############################


def get_group_info(group_name, session):
    """
    Returns group details
    :group_name: string name of group
    :return: dict object
    """
    access_token = get_user_access_token(session)
    query = {"token": access_token}
    group_info = requests.get(
        ciconnect_api_endpoint + "/v1alpha1/groups/" + group_name, params=query
    )
    group_info = group_info.json()["metadata"]
    return group_info


def get_group_members(group_name, session):
    access_token = get_user_access_token(session)
    query = {"token": access_token}
    group_members = requests.get(
        ciconnect_api_endpoint + "/v1alpha1/groups/" + group_name + "/members",
        params=query,
    )
    group_members = group_members.json()["memberships"]
    return group_members


def get_group_members_emails(group_name):
    query = {"token": ciconnect_api_token}

    group_members = get_group_members(group_name, session)
    multiplexJson = {}
    users_statuses = {}
    # Get detailed user information from list of users
    for user in group_members:
        unix_name = user["user_name"]
        user_state = user["state"]
        if user_state != "nonmember" and unix_name != "root":
            user_query = "/v1alpha1/users/" + unix_name + "?token=" + query["token"]
            multiplexJson[user_query] = {"method": "GET"}
            users_statuses[unix_name] = user_state

    # POST request for multiplex return
    multiplex = get_multiplex(multiplexJson)
    user_dict = {}
    group_user_dict = {}

    for user in multiplex:
        user_name = user.split("/")[3].split("?")[0]
        user_dict[user_name] = json.loads(multiplex[user]["body"])

    for user, info in user_dict.items():
        for group_membership in info["metadata"]["group_memberships"]:
            if group_membership["name"] == group_name:
                group_user_dict[user] = info

    return user_dict, users_statuses


def delete_group_entry(group_name, session):
    """
    Deletes group entry
    :group_name: string name of group
    :return:
    """
    access_token = get_user_access_token(session)
    query = {"token": access_token}

    r = requests.delete(
        ciconnect_api_endpoint + "/v1alpha1/groups/" + group_name, params=query
    )
    return r


def get_subgroups(group_name, session):
    """
    Returns list of a group's subgroups
    :group_name: string name of group
    :param session: user session to pull primary_identity
    :return: list of dict objects
    """
    access_token = get_user_access_token(session)
    query = {"token": access_token}

    subgroups = requests.get(
        ciconnect_api_endpoint + "/v1alpha1/groups/" + group_name + "/subgroups",
        params=query,
    )
    subgroups = subgroups.json()["groups"]

    return subgroups


def update_user_group_status(group_name, unix_name, status, session):
    """
    Returns user's status in root connect group
    :param group_name: string name of group
    :param unix_name: string user's unix name
    :param status: string status to set (pending, active, admin, nonmember)
    :return:
    """
    access_token = get_user_access_token(session)
    query = {"token": access_token, "globus_id": session["primary_identity"]}

    put_query = {"apiVersion": "v1alpha1", "group_membership": {"state": status}}
    user_status = requests.put(
        ciconnect_api_endpoint
        + "/v1alpha1/groups/"
        + group_name
        + "/members/"
        + unix_name,
        params=query,
        json=put_query,
    )
    return user_status


def list_connect_admins(group_name):
    """
    Return list of admins of connect group
    Return list of nested dictionaries with state, user_name, and state_set_by
    """
    query = {"token": ciconnect_api_token}
    group_members = requests.get(
        ciconnect_api_endpoint
        + "/v1alpha1/groups/"
        + connect_name(group_name)
        + "/members",
        params=query,
    )
    memberships = group_members.json()["memberships"]
    memberships = [member for member in memberships if member["state"] == "admin"]

    return memberships


def get_user_profile(unix_name):

    identity_id = session.get("primary_identity")

    query = {"token": ciconnect_api_token, "globus_id": identity_id}

    profile = requests.get(
        ciconnect_api_endpoint + "/v1alpha1/users/" + unix_name, params=query
    )

    if profile.status_code == requests.codes.ok:
        profile = profile.json()
        return profile
    else:
        err_message = profile.json()["message"]
        print(err_message)
        return None


def get_user_access_token(session):
    user = get_user_info(session)
    if user:
        access_token = user["metadata"]["access_token"]
    else:
        access_token = None
    return access_token


def domain_name_edgecase():
    """"""
    domain_name = request.headers["Host"]

    if "usatlas" in domain_name:
        domain_name = "atlas.ci-connect.net"
    elif "uscms" in domain_name:
        domain_name = "cms.ci-connect.net"
    elif "af" in domain_name:
        domain_name = "af.uchicago.edu"
    elif "test" in domain_name:
        domain_name = "www-test.ci-connect.net"
    elif "uchicago" in domain_name:
        domain_name = "psdconnect.uchicago.edu"
    elif "snowmass21" in domain_name:
        domain_name = "snowmass21.ci-connect.net"

    return domain_name
