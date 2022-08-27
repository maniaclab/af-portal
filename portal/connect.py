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
        logger.info(resp.status)
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
        group_memberships = data["group_memberships"]
        profile = {"username": username, "email": email, "phone": phone, "join_date": join_date, "institution": institution, "name": name, "role": role, "group_memberships": group_memberships}
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

def get_group_info(groupname, date_format="%B %m %Y"):
    resp = requests.get(base_url + "/v1alpha1/groups/" + groupname, params=params)
    if resp.status_code != 200:
        logger.info(resp.status)
        raise Exception("Error getting info for group %s" %groupname)
    group = resp.json()["metadata"]
    group["pending"] = str(group["pending"])
    group["creation_date"] = parse(group["creation_date"]).strftime(date_format)
    return group

def get_group_members(groupname):
    start = time.time()
    usernames = []
    resp = requests.get(base_url + "/v1alpha1/groups/" + groupname + "/members", params=params)
    if resp.status_code != 200:
        logger.info(resp.status)
        raise Exception("Error getting members for group %s" %groupname)
    for entry in resp.json()["memberships"]:
        username = entry["user_name"]
        usernames.append(username)
    stop = time.time()
    logger.info("The get_group_members function has taken %.2f ms", (stop-start)*1000)
    return usernames

def get_subgroups(groupname):
    resp = requests.get(base_url + "/v1alpha1/groups/" + groupname + "/subgroups", params=params)
    if resp.status_code != 200:
        logger.info(resp.status)
        raise Exception("Error getting group %s" %groupname)
    subgroups = resp.json()["groups"]
    return subgroups

def get_subgroup_requests(groupname):
    resp = requests.get(base_url + "/v1alpha1/groups/" + groupname + "/subgroup_requests", params=params)
    if resp.status_code != 200:
        logger.info(resp.status)
        raise Exception("Error getting group %s" %groupname)
    subgroups = resp.json()["groups"]
    return subgroups

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

def approve_subgroup_request(subgroup_name, group_name):
    resp = requests.put(base_url + "/v1alpha1/groups/" + group_name + "/subgroup_requests/" + subgroup_name + "/approve", params=params)
    if resp.status_code == requests.codes.ok:
        logger.info("Approved subgroup request for subgroup %s in group %s" %(subgroup_name, group_name))
        return True
    return False

def deny_subgroup_request(subgroup_name, group_name):
    resp = requests.delete(base_url + "/v1alpha1/groups/" + group_name + "/subgroup_requests/" + subgroup_name, params=params)
    if resp.status_code == requests.codes.ok:
        logger.info("Denied subgroup request for subgroup %s in group %s" %(subgroup_name, group_name))
        return True
    return False