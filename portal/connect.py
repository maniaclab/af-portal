from portal import app, logger
from datetime import datetime
import requests
import json
from dateutil.parser import parse

base_url = app.config["CONNECT_API_ENDPOINT"]
token = app.config["CONNECT_API_TOKEN"]

def find_user(globus_id):
    params = {"token": token, "globus_id": globus_id}
    resp = requests.get(base_url + "/v1alpha1/find_user", params=params).json()
    if resp["kind"] == "User":
        return resp["metadata"]
    return None

def get_user_profile(unix_name, date_format="%B %m %Y"):
    params = {"token": token}
    resp = requests.get(base_url + "/v1alpha1/users/" + unix_name, params=params).json()
    if resp["kind"] == "User":
        profile = resp["metadata"]
        profile["join_date"] = datetime.strptime(profile["join_date"], "%Y-%b-%d %H:%M:%S.%f %Z").strftime(date_format)
        profile["group_memberships"].sort(key = lambda group : group["name"])
        return profile
    return None

def get_user_groups(unix_name):
    profile = get_user_profile(unix_name)
    if not profile:
        return None
    multiplex = {}
    status_lookup = {}
    for group in profile["group_memberships"]:
        group_name = group["name"]
        member_status = group["state"]
        status_lookup[group_name] = member_status
        query = "/v1alpha1/groups/" + group_name+ "?token=" + token
        multiplex[query] = {"method": "GET"}
    resp = get_multiplex(multiplex)
    groups = []
    for query in resp:
        if resp[query]["status"] == 200:
            group = json.loads(resp[query]["body"])["metadata"]
            group_name = group["name"]
            group["member_status"] = status_lookup[group_name]
            groups.append(group)
    groups.sort(key = lambda group : group["name"])
    return groups

def update_user_profile(unix_name, **kwargs):
    params = {"token": token}
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
    if resp.status_code == 200:
        logger.info("Updated profile for user %s." %unix_name)
        return True
    return False

def update_user_institution(unix_name, institution):
    params = {"token": token}
    json = {'apiVersion': 'v1alpha1', 'kind': 'User', 'metadata': {'institution': institution}}
    resp = requests.put(base_url + "/v1alpha1/users/" + unix_name, params=params, json=json)
    if resp.status_code == 200:
        logger.info("Updated user %s. Set institution to %s." %(unix_name, institution))
        return True
    return False

def get_multiplex(json):
    params = {"token": token}
    return requests.post(base_url + "/v1alpha1/multiplex", params=params, json=json).json()

def get_member_status(unix_name):
    profile = get_user_profile(unix_name)
    result = list(filter(lambda g : g["name"] == "root.atlas-af", profile["group_memberships"]))
    if len(result) == 0:
        return "nonmember"
    member_status = result[0]["state"]
    return member_status

def get_group_info(groupname, date_format="%B %m %Y"):
    params = {"token": token}
    resp = requests.get(base_url + "/v1alpha1/groups/" + groupname, params=params)
    if resp.status_code != 200:
        logger.info(resp.status)
        raise Exception("Error getting info for group %s" %groupname)
    group = resp.json()["metadata"]
    group["pending"] = str(group["pending"])
    group["creation_date"] = parse(group["creation_date"]).strftime(date_format)
    return group

def get_group_members(groupname, date_format="%B %m %Y"):
    members = {"active": [], "pending": []}
    params = {"token": token}

    resp = requests.get(base_url + "/v1alpha1/groups/" + groupname + "/members", params=params)
    if resp.status_code != 200:
        logger.info(resp.status)
        raise Exception("Error getting members for group %s" %groupname)

    multiplex = {}
    for entry in resp.json()["memberships"]:
        multiplex["/v1alpha1/users/" + entry["user_name"] + "?token=" + token] = {"method": "GET"}
    
    resp = requests.post(base_url + "/v1alpha1/multiplex", params=params, json=multiplex)
    if resp.status_code != 200:
        logger.info(resp.status)
        raise Exception("Error getting members for group %s" %groupname)

    resp = resp.json()
    for entry in resp:
        data = json.loads(resp[entry]["body"])["metadata"]
        username = data["unix_name"]
        email = data["email"]
        phone = data["phone"]
        join_date = parse(data["join_date"]).strftime(date_format) if date_format else parse(data["join_date"]) 
        institution = data["institution"]
        name = data["name"]
        group_membership = next(filter(lambda group : group["name"] == "root.atlas-af", data["group_memberships"]))
        status = group_membership["state"]
        user = {"username": username, "email": email, "phone": phone, "join_date": join_date, "institution": institution, "name": name, "status": status}
        if status in ("admin", "active"):
            members["active"].append(user)
        elif status == "pending":
            members["pending"].append(user)

    return members

def get_subgroups(groupname):
    params = {"token": token}
    resp = requests.get(base_url + "/v1alpha1/groups/" + groupname + "/subgroups", params=params)
    if resp.status_code != 200:
        logger.info(resp.status)
        raise Exception("Error getting group %s" %groupname)
    subgroups = resp.json()["groups"]
    return subgroups

def get_subgroup_requests(groupname):
    params = {"token": token}
    resp = requests.get(base_url + "/v1alpha1/groups/" + groupname + "/subgroup_requests", params=params)
    if resp.status_code != 200:
        logger.info(resp.status)
        raise Exception("Error getting group %s" %groupname)
    subgroups = resp.json()["groups"]
    return subgroups