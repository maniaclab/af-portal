"""
A wrapper for the CI Connect API.

Functionality:
===============
1. get_username looks up a username for a Globus ID
2. get_usernames gets the usernames for a group
3. get_user_profile looks up a user profile
4. get_user_profiles gets the profiles of all users in a group
5. create_user_profile creates a user profile with the given settings
6. update_user_profile updates a user profile with the given settings
7. get_user_groups gets all of a user's groups
8. remove_user_from_group removes a user from a group
9. get_user_roles gets all of a user's roles
10. update_user_role updates a user's role in a group
11. get_group_info gets the info for a group
12. update_group_info updates a group with the given settings
13. remove_group removes a group
14. get_subgroups gets the subgroups of a group
15. create_subgroup creates a subgroup with the given settings

Dependencies:
===============

A portal.conf file properly filled out, with the URL of the Connect API and a token for the Connect API.
The portal.conf file should be saved in the directory af-portal/portal/secrets.

Example usage:
===============

Example #1:

cd <path>/<to>/af-portal
python
>>> from portal import connect
>>> username = connect.get_username('alphanumeric-globus-id')
>>> print(username)

Example #2:

cd <path>/<to>/af-portal
python
>>> from portal import connect
>>> from pprint import pprint
>>> profile = connect.get_user_proflie('myusername')
>>> pprint(profile)

Example #3:

cd <path>/<to>/af-portal
python
>>> from portal import connect
>>> from pprint import pprint
>>> profiles = connect.get_user_profiles('root.atlas-af')
>>> pprint(profiles)

Example #4:

cd <path>/<to>/af-portal
python
>>> from portal import connect
>>> from pprint import pprint
>>> connect.update_user_profile('myusername', public_key='<ssh public key here>')
>>> profile = connect.get_user_profile('myusername')
>>> pprint(profile)

Example #5:

cd <path>/<to>/af-portal
python
>>> from portal import connect
>>> from pprint import pprint
>>> info = connect.get_group_info('root.atlas-af', date_format='calendar')
>>> pprint(info)
"""

from portal import logger, decorators
from portal.app import app
from portal.errors import ConnectApiError
from dateutil.parser import parse
import requests
import json

url = app.config.get("CONNECT_API_ENDPOINT")
token = app.config.get("CONNECT_API_TOKEN")


def get_username(globus_id):
    """Looks up the username for a globus ID."""
    response = requests.get(
        url + "/v1alpha1/find_user", params={"token": token, "globus_id": globus_id}
    )
    if response.text:
        data = response.json()
        if data.get("kind") == "Error":
            logger.error(data["message"])
        if data.get("kind") == "User":
            return data["metadata"]["unix_name"]
    return None


def get_usernames(group_name, **options):
    """Returns a list of usernames for users in the specified group."""
    response = requests.get(
        url + "/v1alpha1/groups/" + group_name + "/members", params={"token": token}
    )
    if response.text:
        data = response.json()
        if data.get("kind") == "Error":
            logger.error(data["message"])
            raise ConnectApiError(data["message"])
        usernames = []
        roles = options.get("roles", ("admin", "active", "pending"))
        for membership in data["memberships"]:
            if membership["state"] in roles:
                usernames.append(membership["user_name"])
        return usernames
    return []


def get_user_profile(username, **options):
    """Gets a user profile and returns it as a dictionary."""
    response = requests.get(
        url + "/v1alpha1/users/" + username, params={"token": token}
    )
    if response.text:
        data = response.json()
        if data.get("kind") == "Error":
            logger.error(data["message"])
            raise ConnectApiError(data["message"])
        if data.get("kind") == "User":
            profile = {}
            metadata = data["metadata"]
            profile["unix_name"] = metadata["unix_name"]
            profile["unix_id"] = metadata["unix_id"]
            profile["name"] = metadata["name"]
            profile["email"] = metadata["email"]
            profile["institution"] = metadata["institution"]
            profile["phone"] = metadata["phone"]
            profile["public_key"] = metadata["public_key"]
            if "totp_secret" in metadata.keys():
                profile["totp_secret"] = metadata["totp_secret"]
            date_format = options.get("date_format", "calendar")
            if date_format == "object":
                profile["join_date"] = parse(metadata["join_date"])
            elif date_format == "iso":
                profile["join_date"] = parse(metadata["join_date"]).isoformat()
            elif date_format == "calendar":
                profile["join_date"] = parse(metadata["join_date"]).strftime("%B %m %Y")
            else:
                profile["join_date"] = parse(metadata["join_date"]).strftime(
                    date_format
                )
            profile["group_memberships"] = metadata["group_memberships"]
            profile["group_memberships"].sort(key=lambda group: group["name"])
            membership = list(
                filter(
                    lambda group: group["name"] == "root.atlas-af",
                    metadata["group_memberships"],
                )
            )
            profile["role"] = membership[0]["state"] if membership else "nonmember"
            return profile
    return None


def get_user_profiles(group_name, **options):
    """Gets the profiles of users in a group and returns them as a list of dictionaries."""
    usernames = get_usernames(group_name, **options)
    request_data = {}
    for username in usernames:
        request_data["/v1alpha1/users/" + username + "?token=" + token] = {
            "method": "GET"
        }
    response = requests.post(
        url + "/v1alpha1/multiplex", params={"token": token}, json=request_data
    )
    if response.text:
        data = response.json()
        if data.get("kind") == "Error":
            logger.error(data["message"])
            raise ConnectApiError(data["message"])
        profiles = []
        for value in data.values():
            profile = {}
            metadata = json.loads(value["body"])["metadata"]
            profile["unix_name"] = metadata["unix_name"]
            profile["unix_id"] = metadata["unix_id"]
            profile["name"] = metadata["name"]
            profile["email"] = metadata["email"]
            profile["institution"] = metadata["institution"]
            profile["phone"] = metadata["phone"]
            date_format = options.get("date_format", "calendar")
            if date_format == "object":
                profile["join_date"] = parse(metadata["join_date"])
            elif date_format == "iso":
                profile["join_date"] = parse(metadata["join_date"]).isoformat()
            elif date_format == "calendar":
                profile["join_date"] = parse(metadata["join_date"]).strftime("%B %m %Y")
            else:
                profile["join_date"] = parse(metadata["join_date"]).strftime(
                    date_format
                )
            membership = list(
                filter(
                    lambda group: group["name"] == "root.atlas-af",
                    metadata["group_memberships"],
                )
            )
            profile["role"] = membership[0]["state"] if membership else "nonmember"
            profiles.append(profile)
        return profiles
    return []


@decorators.require_keys(
    "globus_id", "unix_name", "name", "institution", "email", "phone", "public_key"
)
def create_user_profile(**settings):
    """Creates a profile with the given settings."""
    request_data = {
        "apiVersion": "v1alpha1",
        "metadata": {
            "globusID": settings["globus_id"],
            "unix_name": settings["unix_name"],
            "name": settings["name"],
            "institution": settings["institution"],
            "email": settings["email"],
            "phone": settings["phone"],
            "public_key": settings["public_key"],
            "superuser": False,
            "service_account": False,
            "create_totp_secret": True,
        },
    }
    response = requests.post(
        url + "/v1alpha1/users", params={"token": token}, json=request_data
    )
    if response.text:
        data = response.json()
        if data.get("kind") == "Error":
            logger.error(data["message"])
            raise ConnectApiError(data["message"])
    logger.info("Created profile for user %s" % settings["unix_name"])


@decorators.permit_keys(
    "name", "institution", "email", "phone", "public_key", "create_totp_secret"
)
def update_user_profile(username, **settings):
    """Updates a user profile with the given settings."""
    request_data = {"apiVersion": "v1alpha1", "kind": "User", "metadata": settings}
    response = requests.put(
        url + "/v1alpha1/users/" + username, params={"token": token}, json=request_data
    )
    if response.text:
        data = response.json()
        if data.get("kind") == "Error":
            logger.error(data["message"])
            raise ConnectApiError(data["message"])
    logger.info("Updated profile for user %s." % username)


def get_user_groups(username, **options):
    """Gets all of a user's groups and returns them as a list of dictionaries."""
    roles = get_user_roles(username)
    request_data = {}
    for group_name in roles:
        request_data["/v1alpha1/groups/" + group_name + "?token=" + token] = {
            "method": "GET"
        }
    response = requests.post(
        url + "/v1alpha1/multiplex", params={"token": token}, json=request_data
    )
    if response.text:
        data = response.json()
        if data.get("kind") == "Error":
            logger.error(data["message"])
            raise ConnectApiError(data["message"])
        pattern = options.get("pattern", None)
        date_format = options.get("date_format", "calendar")
        groups = []
        for value in data.values():
            if value["status"] == requests.codes.ok:
                group = {}
                metadata = json.loads(value["body"])["metadata"]
                group["name"] = metadata["name"]
                if pattern and not group["name"].startswith(pattern):
                    continue
                group["display_name"] = metadata["display_name"]
                group["description"] = metadata["description"]
                group["email"] = metadata["email"]
                group["phone"] = metadata["phone"]
                group["purpose"] = metadata["purpose"]
                group["unix_id"] = metadata["unix_id"]
                group["pending"] = metadata["pending"]
                if date_format == "object":
                    group["creation_date"] = parse(metadata["creation_date"])
                elif date_format == "iso":
                    group["creation_date"] = parse(
                        metadata["creation_date"]
                    ).isoformat()
                elif date_format == "calendar":
                    group["creation_date"] = parse(metadata["creation_date"]).strftime(
                        "%B %m %Y"
                    )
                else:
                    group["creation_date"] = parse(metadata["creation_date"]).strftime(
                        date_format
                    )
                group["role"] = roles.get(group["name"])
                groups.append(group)
        groups.sort(key=lambda group: group["name"])
        return groups
    return None


def remove_user_from_group(username, group_name):
    """Removes a user from a group."""
    response = requests.delete(
        url + "/v1alpha1/groups/" + group_name + "/members/" + username,
        params={"token": token},
    )
    if response.text:
        data = response.json()
        if data.get("kind") == "Error":
            logger.error(data["message"])
            raise ConnectApiError(data["message"])
    logger.info("Removed user %s from group %s" % (username, group_name))


def get_user_roles(username):
    """Gets all of a user's roles and returns them as a dictionary."""
    profile = get_user_profile(username)
    if profile:
        return {
            group_membership["name"]: group_membership["state"]
            for group_membership in profile["group_memberships"]
        }
    return None


def update_user_role(username, group_name, role):
    """Updates a user's role in a group."""
    request_data = {"apiVersion": "v1alpha1", "group_membership": {"state": role}}
    response = requests.put(
        url + "/v1alpha1/groups/" + group_name + "/members/" + username,
        params={"token": token},
        json=request_data,
    )
    if response.text:
        data = response.json()
        if data.get("kind") == "Error":
            logger.error(data["message"])
            raise ConnectApiError(data["message"])
    logger.info("Set role to %s for user %s in group %s" % (role, username, group_name))


def get_group_info(group_name, **options):
    """Looks up a group and returns its info as a dictionary."""
    response = requests.get(
        url + "/v1alpha1/groups/" + group_name, params={"token": token}
    )
    data = response.json()
    if data.get("kind") == "Error":
        logger.error(data["message"])
        raise ConnectApiError(data["message"])
    if data.get("kind") == "Group":
        group = {}
        metadata = data["metadata"]
        group["name"] = metadata["name"]
        group["display_name"] = metadata["display_name"]
        group["description"] = metadata["description"]
        group["email"] = metadata["email"]
        group["phone"] = metadata["phone"]
        group["purpose"] = metadata["purpose"]
        group["unix_id"] = metadata["unix_id"]
        group["pending"] = metadata["pending"]
        date_format = options.get("date_format", "calendar")
        if date_format == "object":
            group["creation_date"] = parse(metadata["creation_date"])
        elif date_format == "iso":
            group["creation_date"] = parse(metadata["creation_date"]).isoformat()
        elif date_format == "calendar":
            group["creation_date"] = parse(metadata["creation_date"]).strftime(
                "%B %m %Y"
            )
        else:
            group["creation_date"] = parse(metadata["creation_date"]).strftime(
                date_format
            )
        group["is_removable"] = is_group_removable(group_name)
        return group
    return None


@decorators.permit_keys("display_name", "email", "phone", "description")
def update_group_info(group_name, **settings):
    """Updates a group's info with the given settings."""
    request_data = {"apiVersion": "v1alpha1", "metadata": settings}
    response = requests.put(
        url + "/v1alpha1/groups/" + group_name,
        params={"token": token},
        json=request_data,
    )
    if response.text:
        data = response.json()
        if data.get("kind") == "Error":
            logger.error(data["message"])
            raise ConnectApiError(data["message"])
    logger.info("Updated info for group %s" % group_name)


def is_group_removable(group_name):
    if group_name in (
        "root",
        "root.atlas-af",
        "root.atlas-af.staff",
        "root.atlas-af.uchicago",
        "root.atlas-ml",
        "root.atlas-ml.staff",
        "root.iris-hep-ml",
        "root.iris-hep-ml.staff",
        "root.osg",
        "root.osg.login-nodes",
    ):
        return False
    return True


def remove_group(group_name):
    """If a group can be removed, removes the group."""
    if is_group_removable(group_name):
        response = requests.delete(
            url + "/v1alpha1/groups/" + group_name, params={"token": token}
        )
        if response.text:
            data = response.json()
            if data.get("kind") == "Error":
                logger.error(data["message"])
                raise ConnectApiError(data["message"])
        logger.info("Removed group %s" % group_name)
        return True
    return False


def get_subgroups(group_name):
    """Returns the subgroups of a group as a list of dictionaries."""
    response = requests.get(
        url + "/v1alpha1/groups/" + group_name + "/subgroups", params={"token": token}
    )
    if response.text:
        data = response.json()
        if data.get("kind") == "Error":
            logger.error(data["message"])
            raise ConnectApiError(data["message"])
        return data.get("groups")
    return None


@decorators.require_keys(
    "name", "display_name", "email", "phone", "description", "purpose"
)
def create_subgroup(group_name, **settings):
    """Creates a subgroup with the given settings."""
    request_data = {"apiVersion": "v1alpha1", "metadata": settings}
    response = requests.put(
        url
        + "/v1alpha1/groups/"
        + group_name
        + "/subgroup_requests/"
        + settings["name"],
        params={"token": token},
        json=request_data,
    )
    if response.text:
        data = response.json()
        if data.get("kind") == "Error":
            logger.error(data["message"])
            raise ConnectApiError(data["message"])
    logger.info("Created subgroup %s in group %s" % (settings["name"], group_name))
