from portal import app, logger
from datetime import datetime
import requests
import json
from dateutil.parser import parse

base_url = app.config['CONNECT_API_ENDPOINT']
token = app.config['CONNECT_API_TOKEN']
params = {'token': token}
        
def find_user(globus_id):
    params = {'token': token, 'globus_id': globus_id}
    resp = requests.get(base_url + '/v1alpha1/find_user', params=params).json()
    if resp['kind'] == 'User':
        return resp['metadata']
    return None

def get_user_profile(unix_name, date_format='%B %m %Y'):
    resp = requests.get(base_url + '/v1alpha1/users/' + unix_name, params=params).json()
    if resp['kind'] == 'User':
        profile = resp['metadata']
        profile['join_date'] = datetime.strptime(profile['join_date'], '%Y-%b-%d %H:%M:%S.%f %Z').strftime(date_format)
        profile['group_memberships'].sort(key = lambda group : group['name'])
        af_group = next(filter(lambda group : group['name'] == 'root.atlas-af', profile['group_memberships']), None)
        profile['role'] = af_group['state'] if af_group else 'nonmember'
        return profile
    return None

def get_user_profiles(usernames, date_format='%B %m %Y'):
    profiles = []
    multiplex = {}
    for username in usernames:
        multiplex['/v1alpha1/users/' + username + '?token=' + token] = {'method': 'GET'}
    resp = requests.post(base_url + '/v1alpha1/multiplex', params=params, json=multiplex)
    if resp.status_code != requests.codes.ok:
        raise Exception('Error getting user profiles')
    resp = resp.json()
    for entry in resp:
        data = json.loads(resp[entry]['body'])['metadata']
        username = data['unix_name']
        email = data['email']
        phone = data['phone']
        join_date = parse(data['join_date']).strftime(date_format) if date_format else parse(data['join_date']) 
        institution = data['institution']
        name = data['name']
        af_group = next(filter(lambda group : group['name'] == 'root.atlas-af', data['group_memberships']), None)
        role = af_group['state'] if af_group else 'nonmember'
        profile = {'username': username, 'email': email, 'phone': phone, 'join_date': join_date, 'institution': institution, 'name': name, 'role': role}
        profiles.append(profile)
    return profiles 

def create_user_profile(globus_id, unix_name, name, email, phone, institution, public_key):
    json = {
        'apiVersion': 'v1alpha1',
        'metadata': {
            'globusID': globus_id,
            'unix_name': unix_name,
            'name': name,
            'email': email,
            'phone': phone,
            'institution': institution,
            'superuser': False,
            'service_account': False
        }
    }
    if public_key:
        json['metadata']['public_key'] = public_key
    resp = requests.post(base_url + '/v1alpha1/users', params=params, json=json)
    if resp.status_code == requests.codes.ok:
        logger.info('Created profile for user %s' %unix_name)
        return True
    logger.error('Unable to create profile for %s' %name)
    return False

def update_user_profile(unix_name, name=None, email=None, phone=None, institution=None, public_key=None, x509_dn=None):
    json = {
        'apiVersion': 'v1alpha1', 
        'kind': 'User', 
        'metadata': {
            'name': name,
            'email': email,
            'phone': phone,
            'institution': institution,
            'public_key': public_key,
            'X.509_DN': x509_dn
        }
    }    
    resp = requests.put(base_url + '/v1alpha1/users/' + unix_name, params=params, json=json)
    if resp.status_code == requests.codes.ok:
        logger.info('Updated profile for user %s' %unix_name)
        return True
    logger.error('Unable to update profile for user %s' %unix_name)
    return False

def get_user_groups(unix_name):
    profile = get_user_profile(unix_name)
    if not profile:
        return None
    multiplex = {}
    states = {}
    for group in profile['group_memberships']:
        group_name = group['name']
        state = group['state']
        states[group_name] = state
        query = '/v1alpha1/groups/' + group_name+ '?token=' + token
        multiplex[query] = {'method': 'GET'}
    resp = requests.post(base_url + '/v1alpha1/multiplex', params=params, json=multiplex)
    if resp.status_code != requests.codes.ok:
        raise Exception('Error getting groups for user %s' %unix_name)
    resp = resp.json()
    groups = []
    for entry in resp:
        if resp[entry]['status'] == requests.codes.ok:
            group = json.loads(resp[entry]['body'])['metadata']
            group_name = group['name']
            group['role'] = states[group_name]
            groups.append(group)
    groups.sort(key = lambda group : group['name'])
    return groups

def get_group_info(group_name, date_format='%B %m %Y'):
    resp = requests.get(base_url + '/v1alpha1/groups/' + group_name, params=params)
    if resp.status_code != requests.codes.ok:
        raise Exception('Error getting info for group %s' %group_name)
    group = resp.json()['metadata']
    group['pending'] = str(group['pending'])
    group['creation_date'] = parse(group['creation_date']).strftime(date_format)
    group['is_deletable'] = is_group_deletable(group_name)
    return group

def update_group_info(group_name, display_name, email, phone, description):
    json = {
        'apiVersion': 'v1alpha1',
        'metadata': {
            'display_name': display_name,
            'email': email,
            'phone': phone,
            'description': description,
        }
    }
    resp = requests.put(base_url + '/v1alpha1/groups/' + group_name, params=params, json=json)
    if resp.status_code == requests.codes.ok:
        logger.info('Updated info for group %s' %group_name)
        return True
    logger.error('Unable to update info for group %s' %group_name)
    return False

def get_group_members(group_name, states=['admin', 'active', 'pending']):
    usernames = []
    resp = requests.get(base_url + '/v1alpha1/groups/' + group_name + '/members', params=params)
    if resp.status_code != requests.codes.ok:
        raise Exception('Error getting members for group %s' %group_name)
    for entry in resp.json()['memberships']:
        username = entry['user_name']
        if entry['state'] in states:
            usernames.append(username)
    return usernames

def update_user_group_status(unix_name, group_name, status):
    json = {'apiVersion': 'v1alpha1', 'group_membership': {'state': status}}
    resp = requests.put(base_url + '/v1alpha1/groups/' + group_name + '/members/' + unix_name, params=params, json=json)
    if resp.status_code == requests.codes.ok:
        logger.info('Set status to %s for user %s in group %s' %(status, unix_name, group_name))
        return True
    logger.error('Unable to update status for user %s in group %s' %(unix_name, group_name))
    return False

def remove_user_from_group(unix_name, group_name):
    resp = requests.delete(base_url + '/v1alpha1/groups/' + group_name + '/members/' + unix_name, params=params)
    if resp.status_code == requests.codes.ok:
        logger.info('Removed user %s from group %s' %(unix_name, group_name))
        return True
    logger.error('Unable to remove user %s from group %s' %(unix_name, group_name))
    return False

def get_subgroups(group_name):
    resp = requests.get(base_url + '/v1alpha1/groups/' + group_name + '/subgroups', params=params)
    if resp.status_code != requests.codes.ok:
        raise Exception('Error getting group %s' %group_name)
    subgroups = resp.json()['groups']
    return subgroups

def create_subgroup(subgroup_name, display_name, group_name, email, phone, description, purpose):
    json = {
        'apiVersion': 'v1alpha1',
        'metadata': {
            'name': subgroup_name,
            'display_name': display_name,
            'purpose': purpose,
            'email': email,
            'phone': phone,
            'description': description
        }
    }
    resp = requests.put(base_url + '/v1alpha1/groups/' + group_name + '/subgroup_requests/' + subgroup_name, params=params, json=json)
    if resp.status_code == requests.codes.ok:
        logger.info('Created subgroup %s in group %s', subgroup_name, group_name)
        return True
    logger.error('Unable to create subgroup %s in group %s' %(subgroup_name, group_name))
    return False

def is_group_deletable(group_name):
    return group_name not in (
        'root', 
        'root.atlas-af', 
        'root.atlas-af.staff',
        'root.atlas-af.uchicago',
        'root.atlas-ml', 
        'root.atlas-ml.staff', 
        'root.iris-hep-ml',
        'root.iris-hep-ml.staff',
        'root.osg',
        'root.osg.login-nodes')

def delete_group(group_name):
    if is_group_deletable(group_name):
        resp = requests.delete(base_url + '/v1alpha1/groups/' + group_name, params=params)
        if resp.status_code == requests.codes.ok:
            logger.info('Removed group %s' %group_name)
            return True
        logger.error('Unable to remove group %s' %group_name)
    return False