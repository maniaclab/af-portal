import requests
import os
from base64 import b64encode
from portal import app

slate_api_token = app.config["SLATE_API_TOKEN"]
slate_api_endpoint = app.config["SLATE_API_ENDPOINT"]
query = {"token": slate_api_token}

# Install Jupyter


def generateToken():
    token_bytes = os.urandom(32)
    b64_encoded = b64encode(token_bytes).decode()
    return b64_encoded


def get_app_config(app_name):
    query = {"token": slate_api_token, "dev": "true"}
    app_config = requests.get(
        slate_api_endpoint + "/v1alpha3/apps/" + app_name, params=query
    )
    return app_config


def get_app_readme(app_name):
    query = {"token": slate_api_token, "dev": "true"}
    app_readme = requests.get(
        slate_api_endpoint + "/v1alpha3/apps/" + app_name + "/info", params=query
    )
    return app_readme


def create_application():
    """
    Query SLATE API to create application based on config, group, and cluster
    :return:
    """
    app_name = "jupyter-notebook"
    group = "group_2Q9yPCOLxMg"
    cluster = "uchicago-river-v2"

    configuration = get_app_config(app_name)
    configuration = configuration.json()["spec"]["body"]

    install_app = {
        "apiVersion": "v1alpha3",
        "group": group,
        "cluster": cluster,
        "configuration": configuration,
    }

    # Post query to install application config
    app_install = requests.post(
        slate_api_endpoint + "/v1alpha3/apps/" + app_name,
        params=query,
        json=install_app,
    )

    print("APP INSTALL STATUS: {}".format(app_install))
    print("APP NAME: {}".format(app_name))

    create_application = query_status_code(app_install)
    return create_application


#  Users
def get_user_info(session):

    query = {"token": slate_api_token, "globus_id": session["primary_identity"]}

    profile = requests.get(slate_api_endpoint + "/v1alpha3/find_user", params=query)

    profile = profile.json()
    user_id = profile["metadata"]["id"]
    access_token = profile["metadata"]["access_token"]
    return access_token, user_id


def get_user_id(session):

    query = {"token": slate_api_token, "globus_id": session["primary_identity"]}

    profile = requests.get(slate_api_endpoint + "/v1alpha3/find_user", params=query)

    profile = profile.json()
    user_id = profile["metadata"]["id"]
    return user_id


def get_user_access_token(session):

    query = {"token": slate_api_token, "globus_id": session["primary_identity"]}

    profile = requests.get(slate_api_endpoint + "/v1alpha3/find_user", params=query)

    profile = profile.json()
    access_token = profile["metadata"]["access_token"]
    return access_token


def delete_user(userID, query):
    res = requests.delete(slate_api_endpoint + "/v1alpha3/" + userID, params=query)
    print(res)
    res = res.json()
    print(res)
    return res


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


def list_applications_request():
    """
    Returns list of all applications on slate
    :return: list of slate applications
    """
    applications = requests.get(slate_api_endpoint + "/v1alpha3/apps")
    applications = query_status_code(applications)
    return applications


def list_incubator_applications_request():
    """
    Request query to list incubator applications information
    """
    incubator_apps = requests.get(slate_api_endpoint + "/v1alpha3/apps?dev=true")
    # incubator_apps = incubator_apps.json()['items']
    incubator_apps = query_status_code(incubator_apps)
    return incubator_apps


def list_public_groups_request():
    """
    Returns list of all public groups on slate
    :return: list of public groups
    """
    public_groups = requests.get(slate_api_endpoint + "/v1alpha3/groups", params=query)
    public_groups = public_groups.json()["items"]
    return public_groups


def list_clusters_request():
    """
    Returns list of all clusters on slate
    :return: list of slate clusters
    """
    clusters = requests.get(slate_api_endpoint + "/v1alpha3/clusters", params=query)
    clusters = clusters.json()["items"]
    return clusters


def list_instances_request():
    """
    Returns list of all instances on slate
    :return: list of slate instances
    """
    instances = requests.get(slate_api_endpoint + "/v1alpha3/instances", params=query)
    # print("TRYING GET INSTANCES LIST WITH URL: {}".format(instances.url))
    # print("RESPONSE: {}".format(instances.json()))
    instances = instances.json()["items"]
    return instances


def get_instance_details(instance_id):
    """
    Returns json detail of specific instance on slate
    :return: json object of slate instance details
    """
    query = {"token": slate_api_token, "detailed": "true"}
    instance_detail = requests.get(
        slate_api_endpoint + "/v1alpha3/instances/" + instance_id, params=query
    )
    instance_detail = instance_detail.json()
    return instance_detail


def get_instance_logs(instance_id):
    """
    Returns json detail of specific instance on slate
    :return: json object of slate instance details
    """
    instance_logs = requests.get(
        slate_api_endpoint + "/v1alpha3/instances/" + instance_id + "/logs",
        params=query,
    )
    instance_logs = instance_logs.json()
    return instance_logs


def delete_instance(instance_id):
    """
    Query to delete instance based on instance_id
    :return: request response
    """
    response = requests.delete(
        slate_api_endpoint + "/v1alpha3/instances/" + instance_id, params=query
    )
    return response


def list_user_groups(session):
    """
    Returns list of groups that user belongs in
    :param session: session from User accessing information
    :return: list of user's groups
    """
    # Get groups to which the user belongs based on CI-Connect user
    user_groups = requests.get(
        slate_api_endpoint + "/v1alpha3/users/" + "user_YXRvNlN998A" + "/groups",
        params=query,
    )
    user_groups = user_groups.json()["items"]
    return user_groups


def list_users_instances_request(session):
    """
    Returns sorted list of instances associated with specific user
    :param session: session from User accessing information
    :return: list of instances belonging to a specific user
    """
    # Get list of all instances
    instances = list_instances_request()
    # print("Instances: {}".format(instances))
    # Get groups to which the user belongs
    user_groups_list = list_user_groups(session)
    # print("User Groups: {}".format(user_groups_list))
    user_groups = []
    # Set up nice list of user group's name
    for groups in user_groups_list:
        user_groups.append(groups["metadata"]["name"])
    # print("user_groups: {}".format(user_groups))
    # Logic to isolate instances belonging to specific user
    user_instances = []
    for instance in instances:
        if (instance["metadata"]["group"] in user_groups) and (
            "-{}-".format(session["unix_name"]) in instance["metadata"]["name"]
        ):
            user_instances.append(instance)
    # print("User instances: {}".format(user_instances))
    # Return list of instances in sorted order
    sorted_instances = sorted(user_instances, key=lambda i: i["metadata"]["name"])
    return sorted_instances


def list_connect_admins(group_name):
    """
    Return list of admins of connect group
    Return list of nested dictionaries with state, user_name, and state_set_by
    """
    query = {"token": slate_api_token}
    group_members = requests.get(
        slate_api_endpoint
        + "/v1alpha1/groups/"
        + connect_name(group_name)
        + "/members",
        params=query,
    )
    memberships = group_members.json()["memberships"]
    memberships = [member for member in memberships if member["state"] == "admin"]

    return memberships
