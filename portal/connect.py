from portal import app, logger
from datetime import datetime
import requests
import json
from dateutil.parser import parse
import time

base_url = app.config["CONNECT_API_ENDPOINT"]
token = app.config["CONNECT_API_TOKEN"]
params = {"token": token}

def find_user(globus_id):
    params = {"token": token, "globus_id": globus_id}
    resp = requests.get(base_url + "/v1alpha1/find_user", params=params).json()
    if resp["kind"] == "User":
        return resp["metadata"]
    return None

def get_user_profile(unix_name, date_format="%B %m %Y"):
    resp = requests.get(base_url + "/v1alpha1/users/" + unix_name, params=params).json()
    if resp["kind"] == "User":
        profile = resp["metadata"]
        profile["join_date"] = datetime.strptime(profile["join_date"], "%Y-%b-%d %H:%M:%S.%f %Z").strftime(date_format)
        profile["group_memberships"].sort(key = lambda group : group["name"])
        role = next(filter(lambda group : group["name"] == "root.atlas-af", profile["group_memberships"]), None)
        profile["role"] = role["state"] if role else "nonmember"
        return profile
    return None

def get_multiplex(json):
    return requests.post(base_url + "/v1alpha1/multiplex", params=params, json=json).json()

def get_user_profiles(usernames, date_format="%B %m %Y"):
    start = time.time()
    profiles = []
    multiplex = {}
    for username in usernames:
        multiplex["/v1alpha1/users/" + username + "?token=" + token] = {"method": "GET"}
    resp = requests.post(base_url + "/v1alpha1/multiplex", params=params, json=multiplex)
    if resp.status_code != 200:
        raise Exception("Error getting user profiles")
    resp = resp.json()
    for entry in resp:
        data = json.loads(resp[entry]["body"])["metadata"]
        username = data["unix_name"]
        email = data["email"]
        phone = data["phone"]
        join_date = parse(data["join_date"]).strftime(date_format) if date_format else parse(data["join_date"]) 
        institution = data["institution"]
        name = data["name"]
        group = list(filter(lambda group : group["name"] == "root.atlas-af", data["group_memberships"]))
        role = "nonmember"
        if (len(group) == 1):
            role = group[0]["state"]
        profile = {"username": username, "email": email, "phone": phone, "join_date": join_date, "institution": institution, "name": name, "role": role}
        profiles.append(profile)
    stop = time.time()
    logger.info("The get_user_profiles function has taken %.2f ms", (stop-start)*1000)
    return profiles 

def get_user_role(unix_name):
    profile = get_user_profile(unix_name)
    group = list(filter(lambda group : group["name"] == "root.atlas-af", profile["group_memberships"]))
    if len(group) == 0:
        return "nonmember"
    return group[0]["state"]

def update_user_profile(unix_name, **kwargs):
    json = {
        "apiVersion": "v1alpha1",
        "metadata": {
            "name": kwargs["name"],
            "email": kwargs["email"],
            "phone": kwargs["phone"],
            "institution": kwargs["institution"],
            "public_key": kwargs["public_key"],
            "X.509_DN": kwargs["x509_dn"]
        }
    }
    resp = requests.put(base_url + "/v1alpha1/users/" + unix_name, params=params, json=json)
    if resp.status_code == requests.codes.ok:
        logger.info("Updated profile for user %s." %unix_name)
        return True
    return False

def update_user_institution(unix_name, institution):
    json = {'apiVersion': 'v1alpha1', 'kind': 'User', 'metadata': {'institution': institution}}
    resp = requests.put(base_url + "/v1alpha1/users/" + unix_name, params=params, json=json)
    if resp.status_code == requests.codes.ok:
        logger.info("Updated user %s. Set institution to %s." %(unix_name, institution))
        return True
    return False

def get_user_groups(unix_name):
    profile = get_user_profile(unix_name)
    if not profile:
        return None
    multiplex = {}
    states = {}
    for group in profile["group_memberships"]:
        group_name = group["name"]
        state = group["state"]
        states[group_name] = state
        query = "/v1alpha1/groups/" + group_name+ "?token=" + token
        multiplex[query] = {"method": "GET"}
    resp = get_multiplex(multiplex)
    groups = []
    for query in resp:
        if resp[query]["status"] == 200:
            group = json.loads(resp[query]["body"])["metadata"]
            group_name = group["name"]
            group["role"] = states[group_name]
            groups.append(group)
    groups.sort(key = lambda group : group["name"])
    return groups

def get_group_info(group_name, date_format="%B %m %Y"):
    resp = requests.get(base_url + "/v1alpha1/groups/" + group_name, params=params)
    if resp.status_code != 200:
        raise Exception("Error getting info for group %s" %group_name)
    group = resp.json()["metadata"]
    group["pending"] = str(group["pending"])
    group["creation_date"] = parse(group["creation_date"]).strftime(date_format)
    group["is_deletable"] = is_group_deletable(group_name)
    return group

def get_group_members(group_name, states=["admin", "active", "pending"]):
    usernames = []
    resp = requests.get(base_url + "/v1alpha1/groups/" + group_name + "/members", params=params)
    if resp.status_code != 200:
        raise Exception("Error getting members for group %s" %group_name)
    for entry in resp.json()["memberships"]:
        username = entry["user_name"]
        if entry["state"] in states:
            usernames.append(username)
    return usernames

def get_subgroups(group_name):
    resp = requests.get(base_url + "/v1alpha1/groups/" + group_name + "/subgroups", params=params)
    if resp.status_code != 200:
        raise Exception("Error getting group %s" %group_name)
    subgroups = resp.json()["groups"]
    return subgroups

def get_subgroup_requests(group_name):
    resp = requests.get(base_url + "/v1alpha1/groups/" + group_name + "/subgroup_requests", params=params)
    if resp.status_code != 200:
        raise Exception("Error getting group %s" %group_name)
    subgroups = resp.json()["groups"]
    return subgroups

def update_user_group_status(unix_name, group_name, status):
    json = {"apiVersion": "v1alpha1", "group_membership": {"state": status}}
    resp = requests.put(base_url + "/v1alpha1/groups/" + group_name + "/members/" + unix_name, params=params, json=json)
    if resp.status_code == requests.codes.ok:
        logger.info("Set status to %s in group %s for user %s" %(status, group_name, unix_name))
        return True
    return False

def add_user_to_group(unix_name, group_name):
    json = {"apiVersion": "v1alpha1", "group_membership": {"state": "active"}}
    resp = requests.put(base_url + "/v1alpha1/groups/" + group_name + "/members/" + unix_name, params=params, json=json)
    if resp.status_code == requests.codes.ok:
        logger.info("Added user %s to group %s" %(unix_name, group_name))
        return True
    return False

def remove_user_from_group(unix_name, group_name):
    resp = requests.delete(base_url + "/v1alpha1/groups/" + group_name + "/members/" + unix_name, params=params)
    if resp.status_code == requests.codes.ok:
        logger.info("Removed user %s from group %s" %(unix_name, group_name))
        return True
    return False

def create_subgroup(subgroup_name, group_name, **kwargs):
    json = {
        "apiVersion": "v1alpha1",
        "metadata": {
            "name": kwargs["name"],
            "display_name": kwargs["display_name"],
            "purpose": kwargs["purpose"],
            "email": kwargs["email"],
            "phone": kwargs["phone"],
            "description": kwargs["description"]
        }
    }
    resp = requests.put(base_url + "/v1alpha1/groups/" + group_name + "/subgroup_requests/" + subgroup_name, params=params, json=json)
    if resp.status_code == requests.codes.ok:
        return True
    return False

def approve_subgroup_request(subgroup_name, group_name):
    resp = requests.put(base_url + "/v1alpha1/groups/" + group_name + "/subgroup_requests/" + subgroup_name + "/approve", params=params)
    if resp.status_code == requests.codes.ok:
        logger.info("Approved request for subgroup %s in group %s" %(subgroup_name, group_name))
        return True
    return False

def deny_subgroup_request(subgroup_name, group_name):
    resp = requests.delete(base_url + "/v1alpha1/groups/" + group_name + "/subgroup_requests/" + subgroup_name, params=params)
    if resp.status_code == requests.codes.ok:
        logger.info("Denied request for subgroup %s in group %s" %(subgroup_name, group_name))
        return True
    return False

def update_group_info(group_name, **kwargs):
    json = {
        "apiVersion": "v1alpha1",
        "metadata": {
            "display_name": kwargs["display_name"],
            "email": kwargs["email"],
            "phone": kwargs["phone"],
            "description": kwargs["description"],
        }
    }
    resp = requests.put(base_url + "/v1alpha1/groups/" + group_name, params=params, json=json)
    if resp.status_code == requests.codes.ok:
        return True
    return False

def is_group_deletable(group_name):
    return group_name not in (
        'root', 
        'root.atlas-af', 
        'root.atlas-af.staff',
        'root.atlas-af.uchicago',
        'root.atlas-ml', 
        'root.atlas-ml.staff', 
        'root.iris-hep-ssl',
        'root.iris-hep-ssl.staff')

def delete_group(group_name):
    if is_group_deletable(group_name):
        try:
            resp = requests.delete(base_url + "/v1alpha1/groups/" + group_name, params=params)
            return resp.status_code == requests.codes.ok
        except Exception as err:
            logger.info(str(err))
    return False