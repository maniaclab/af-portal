from portal import app, logger
from datetime import datetime
import requests
import json
from dateutil.parser import parse

base_url = app.config["CONNECT_API_ENDPOINT"]
token = app.config["CONNECT_API_TOKEN"]

def find_user(globus_id):
    try: 
        params = {"token": token, "globus_id": globus_id}
        return requests.get(base_url + "/v1alpha1/find_user", params=params).json()
    except Exception as err:
        logger.error(str(err))
        return None

def get_user_profile(unix_name, date_format="%B %m %Y"):
    try: 
        params = {"token": token}
        profile = requests.get(base_url + "/v1alpha1/users/" + unix_name, params=params).json()["metadata"]
        profile["join_date"] = datetime.strptime(profile["join_date"], "%Y-%b-%d %H:%M:%S.%f %Z").strftime(date_format)
        profile["group_memberships"].sort(key = lambda group : group["name"])
        return profile
    except Exception as err:
        logger.error(str(err))
        return None

def get_user_groups(unix_name):
    try: 
        profile = get_user_profile(unix_name)
        multiplex = {}
        status_lookup = {}
        for group in profile["group_memberships"]:
            group_name = group["name"]
            member_status = group["state"]
            status_lookup[group_name] = member_status
            query = "/v1alpha1/groups/" + group_name+ "?token=" + token
            multiplex[query] = {"method": "GET"}
        output = get_multiplex(multiplex)
        groups = []
        for query in output:
            if output[query]["status"] == 200:
                group = json.loads(output[query]["body"])["metadata"]
                group_name = group["name"]
                group["member_status"] = status_lookup[group_name]
                groups.append(group)
        groups.sort(key = lambda group : group["name"])
        return groups
    except Exception as err:
        logger.error(str(err))
        return None

def update_user_profile(unix_name, **kwargs):
    try:
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
        requests.put(base_url + "/v1alpha1/users/" + unix_name, params=params, json=json)
        return True
    except Exception as err:
        logger.error(str(err))
        return False

def get_multiplex(json):
    try:
        params = {"token": token}
        return requests.post(base_url + "/v1alpha1/multiplex", params=params, json=json).json()
    except Exception as err:
        logger.error(str(err))
        return None

def get_member_status(unix_name):
    try:
        profile = get_user_profile(unix_name)
        group = next(filter(lambda g : g["name"] == "root.atlas-af", profile["group_memberships"]))
        member_status = group["state"]
        return member_status
    except:
        return "nonmember"

def get_group_members(groupname, date_format="%B %m %Y"):
    try:
        members = requests.get(base_url + "/v1alpha1/groups/" + groupname + "/members", params={"token": token}).json()["memberships"]
        multiplex = {}
        params = {"token": token}
        for member in members:
            multiplex["/v1alpha1/users/" + member["user_name"] + '?token=' + token] = {"method": "GET"}
        resp = requests.post(base_url + "/v1alpha1/multiplex", params=params, json=multiplex).json()
        profiles = []
        for entry in resp:
            user = json.loads(resp[entry]["body"])["metadata"]
            username = user["unix_name"]
            email = user["email"]
            phone = user["phone"]
            join_date = parse(user["join_date"]).strftime(date_format) if date_format else parse(user["join_date"]) 
            institution = user["institution"]
            name = user["name"]
            group_membership = next(filter(lambda g : g["name"] == "root.atlas-af", user["group_memberships"]))
            status = group_membership["state"]
            profiles.append({"username": username, "email": email, "phone": phone, "join_date": join_date, "institution": institution, "name": name, "status": status})
        return profiles
    except Exception as err: 
        logger.error(str(err))
        return []

def update_user_institution(unix_name, institution):
    try:
        params = {"token": token}
        json = {'apiVersion': 'v1alpha1', 'kind': 'User', 'metadata': {'institution': institution}}
        requests.put(base_url + "/v1alpha1/users/" + unix_name, params=params, json=json)
        logger.info("Updated user %s. Set institution to %s." %(unix_name, institution))
        return True
    except Exception as err:
        logger.error(str(err))
        return False

def get_group_info(group, date_format="%B %m %Y"):
    group_info = requests.get(base_url + "/v1alpha1/groups/" + group, params={"token": token}).json()["metadata"]
    if "pending" in group_info:
        group_info["pending"] = "true" if group_info["pending"] else "false"
    group_info["creation_date"] = parse(group_info["creation_date"]).strftime(date_format)
    return group_info

def get_subgroups(group):
    params = {"token": token}
    subgroups = requests.get(base_url + "/v1alpha1/groups/" + group + "/subgroups", params=params).json()["groups"]
    return subgroups