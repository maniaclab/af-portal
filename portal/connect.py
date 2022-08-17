from portal import app, logger
from datetime import datetime
import requests
import json

def find_user(globus_id):
    try: 
        base_url = app.config["CONNECT_API_ENDPOINT"]
        params = {"token": app.config["CONNECT_API_TOKEN"], "globus_id": globus_id}
        return requests.get(base_url + "/v1alpha1/find_user", params=params).json()
    except Exception as e:
        logger.error(str(e))
        return None

def get_user_profile(unix_name, globus_id):
    try: 
        base_url = app.config["CONNECT_API_ENDPOINT"]
        params = {"token": app.config["CONNECT_API_TOKEN"], "globus_id": globus_id}
        profile = requests.get(base_url + "/v1alpha1/users/" + unix_name, params=params).json()["metadata"]
        profile["join_date"] = datetime.strptime(profile["join_date"], "%Y-%b-%d %H:%M:%S.%f %Z").strftime("%B %m %Y")
        profile["group_memberships"].sort(key = lambda group : group["name"])
        return profile
    except Exception as e:
        logger.error(str(e))
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
            query = "/v1alpha1/groups/" + group_name+ "?token=" + app.config["CONNECT_API_TOKEN"]
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
    except Exception as e:
        logger.error(str(e))
        return None

def update_user_profile(unix_name, globus_id, **kwargs):
    try:
        base_url = app.config["CONNECT_API_ENDPOINT"]
        params = {"token": app.config["CONNECT_API_TOKEN"], "globus_id": globus_id}
        data = {
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
        requests.put(base_url + "/v1alpha1/users/" + unix_name, params=params, json=data)
        return True
    except Exception as e:
        logger.error(str(e))
        return False

def get_multiplex(json):
    try:
        base_url = app.config["CONNECT_API_ENDPOINT"]
        params = {"token": app.config["CONNECT_API_TOKEN"]}
        return requests.post(base_url + "/v1alpha1/multiplex", params=params, json=json).json()
    except Exception as e:
        logger.error(str(e))
        return None

def get_member_status(unix_name, globus_id):
    try:
        profile = get_user_profile(unix_name, globus_id)
        group = next(filter(lambda g : g["name"] == "root.atlas-af", profile["group_memberships"]))
        return group["state"]
    except:
        return "nonmember"
