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

def get_user_profile(unix_name, globus_id):
    try: 
        params = {"token": token, "globus_id": globus_id}
        profile = requests.get(base_url + "/v1alpha1/users/" + unix_name, params=params).json()["metadata"]
        profile["join_date"] = datetime.strptime(profile["join_date"], "%Y-%b-%d %H:%M:%S.%f %Z").strftime("%B %m %Y")
        profile["group_memberships"].sort(key = lambda group : group["name"])
        return profile
    except Exception as err:
        logger.error(str(err))
        return None

def get_user_groups(unix_name, globus_id):
    try: 
        profile = get_user_profile(unix_name, globus_id)
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

def update_user_profile(unix_name, globus_id, **kwargs):
    try:
        params = {"token": token, "globus_id": globus_id}
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

def get_member_status(unix_name, globus_id):
    try:
        profile = get_user_profile(unix_name, globus_id)
        group = next(filter(lambda g : g["name"] == "root.atlas-af", profile["group_memberships"]))
        return group["state"]
    except:
        return "nonmember"

def get_usernames(group):
    try:
        users = requests.get(base_url + "/v1alpha1/groups/" + group + "/members", params={"token": token}).json()
        return [member['user_name'] for member in users["memberships"]]
    except Exception as err:
        logger.error(str(err))
        return []

def get_user_profiles(group, date_format="string"):
    try:
        usernames = get_usernames(group)
        multiplex_json = {}
        params = {"token": token}
        for username in usernames:
            multiplex_json['/v1alpha1/users/' + username + '?token=' + token] = {'method': 'GET'}
        data = requests.post(base_url + '/v1alpha1/multiplex', params=params, json=multiplex_json).json()
        profiles = []
        for entry in data:
            user = json.loads(data[entry]['body'])
            username = user['metadata']['unix_name']
            email = user['metadata']['email']
            join_date = parse(user['metadata']['join_date']) if date_format=='object' else parse(user['metadata']['join_date']).strftime('%Y-%m-%d')
            institution = user['metadata']['institution']
            name = user['metadata']['name']
            profiles.append({'username': username, 'email': email, 'join_date': join_date, 'institution': institution, 'name': name})
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

def get_group_info(group):
    group_info = requests.get(base_url + "/v1alpha1/groups/" + group, params={"token": token}).json()["metadata"]
    if "pending" in group_info:
        group_info["pending"] = "true" if group_info["pending"] else "false"
    group_info["creation_date"] = parse(group_info["creation_date"]).strftime("%B %m %Y")
    return group_info