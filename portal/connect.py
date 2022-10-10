''' A wrapper for the CI Connect API. '''
from portal import app, logger, decorators
from portal.errors import ConnectApiError
from dateutil.parser import parse
import requests
import json

url = app.config.get('CONNECT_API_ENDPOINT')
token = app.config.get('CONNECT_API_TOKEN')

def get_username(globus_id):
    response = requests.get(url + '/v1alpha1/find_user', params={'token': token, 'globus_id': globus_id})
    if response.text:
        data = response.json()
        if data.get('kind') == 'Error':
            logger.error(data['message'])
            raise ConnectApiError(data['message'])
        if data.get('kind') == 'User':
            return data['metadata']['unix_name']
    return None

def get_usernames(group_name, **options):
    response = requests.get(url + '/v1alpha1/groups/' + group_name + '/members', params={'token': token})
    if response.text:
        data = response.json()
        if data.get('kind') == 'Error':
            logger.error(data['message'])
            raise ConnectApiError(data['message'])
        usernames = []
        roles = options.get('roles', ('admin', 'active', 'pending'))
        for membership in response.json()['memberships']:
            if membership['state'] in roles:
                usernames.append(membership['user_name'])
        return usernames
    return []

def get_user_profile(username, **options):
    response = requests.get(url + '/v1alpha1/users/' + username, params={'token': token})
    if response.text:
        data = response.json()
        if data.get('kind') == 'Error':
            logger.error(data['message'])
            raise ConnectApiError(data['message'])
        if data.get('kind') == 'User':
            profile = {}
            metadata = data['metadata']
            profile['unix_name'] = metadata['unix_name']
            profile['unix_id'] = metadata['unix_id']
            profile['name'] = metadata['name']
            profile['email'] = metadata['email']
            profile['institution'] = metadata['institution']
            profile['phone'] = metadata['phone']
            profile['public_key'] = metadata['public_key']
            date_format = options.get('date_format', 'calendar')
            if date_format == 'object':
                profile['join_date'] = parse(metadata['join_date'])
            elif date_format == 'iso':
                profile['join_date'] = parse(metadata['join_date']).isoformat()
            elif date_format == 'calendar':
                profile['join_date'] = parse(metadata['join_date']).strftime('%B %m %Y')
            else:
                profile['join_date'] = parse(metadata['join_date']).strftime(date_format)
            profile['group_memberships'] = metadata['group_memberships']
            profile['group_memberships'].sort(key = lambda group : group['name'])
            membership = list(filter(lambda group : group['name'] == 'root.atlas-af', metadata['group_memberships']))
            profile['role'] = membership[0]['state'] if membership else 'nonmember'
            return profile
    return None

def get_user_profiles(group_name, **options):
    usernames = get_usernames(group_name, **options)
    request_data = {}
    for username in usernames:
        request_data['/v1alpha1/users/' + username + '?token=' + token] = {'method': 'GET'}
    response = requests.post(url + '/v1alpha1/multiplex', params={'token': token}, json=request_data)
    if response.text:
        data = response.json()
        if data.get('kind') == 'Error':
            logger.error(data['message'])
            raise ConnectApiError(data['message'])
        profiles = []
        for value in data.values():
            profile = {}
            metadata = json.loads(value['body'])['metadata']
            profile['unix_name'] = metadata['unix_name']
            profile['unix_id'] = metadata['unix_id']
            profile['name'] = metadata['name']
            profile['email'] = metadata['email']
            profile['institution'] = metadata['institution']
            profile['phone'] = metadata['phone']
            date_format = options.get('date_format', 'calendar')
            if date_format == 'object':
                profile['join_date'] = parse(metadata['join_date'])
            elif date_format == 'iso':
                profile['join_date'] = parse(metadata['join_date']).isoformat()
            elif date_format == 'calendar':
                profile['join_date'] = parse(metadata['join_date']).strftime('%B %m %Y')
            else:
                profile['join_date'] = parse(metadata['join_date']).strftime(date_format)
            membership = list(filter(lambda group : group['name'] == 'root.atlas-af', metadata['group_memberships']))
            profile['role'] = membership[0]['state'] if membership else 'nonmember'
            profiles.append(profile)
        return profiles
    return [] 

@decorators.require_keys('globus_id', 'unix_name', 'name', 'institution', 'email', 'phone', 'public_key')
def create_user_profile(**settings):
    request_data = {
        'apiVersion': 'v1alpha1',
        'metadata': {
            'globusID': settings['globus_id'],
            'unix_name': settings['unix_name'],
            'name': settings['name'],
            'institution': settings['institution'],
            'email': settings['email'],
            'phone': settings['phone'],
            'public_key': settings['public_key'],
            'superuser': False,
            'service_account': False
        }
    }
    response = requests.post(url + '/v1alpha1/users', params={'token': token}, json=request_data)
    if response.text:
        data = response.json()
        if data.get('kind') == 'Error':
            logger.error(data['message'])
            raise ConnectApiError(data['message'])
    logger.info('Created profile for user %s' %settings['unix_name'])

@decorators.permit_keys('name', 'institution', 'email', 'phone', 'public_key')
def update_user_profile(username, **settings):
    request_data = {'apiVersion': 'v1alpha1', 'kind': 'User', 'metadata': settings}
    response = requests.put(url + '/v1alpha1/users/' + username, params={'token': token}, json=request_data)
    if response.text:
        data = response.json()
        if data.get('kind') == 'Error':
            logger.error(data['message'])
            raise ConnectApiError(data['message'])
    logger.info('Updated profile for user %s.' %username)

def get_user_roles(username):
    profile = get_user_profile(username)
    if profile:
        return {group_membership['name'] : group_membership['state'] for group_membership in profile['group_memberships']}
    return None

def get_user_groups(username, **options):
    roles = get_user_roles(username)
    request_data = {}
    for group_name in roles:
        request_data['/v1alpha1/groups/' + group_name + '?token=' + token] = {'method': 'GET'}
    response = requests.post(url + '/v1alpha1/multiplex', params={'token': token}, json=request_data)
    if response.text:
        data = response.json()
        if data.get('kind') == 'Error':
            logger.error(data['message'])
            raise ConnectApiError(data['message'])
        groups = []
        for value in data.values():
            if value['status'] == requests.codes.ok:
                group = {}
                metadata = json.loads(value['body'])['metadata']
                group['name'] = metadata['name']
                group['display_name'] = metadata['display_name']
                group['description'] = metadata['description']
                group['email'] = metadata['email']
                group['phone'] = metadata['phone']
                group['purpose'] = metadata['purpose']
                group['unix_id'] = metadata['unix_id']
                group['pending'] = metadata['pending']
                date_format = options.get('date_format', 'calendar')
                if date_format == 'object':
                    group['creation_date'] = parse(metadata['creation_date'])
                elif date_format == 'iso':
                    group['creation_date'] = parse(metadata['creation_date']).isoformat()
                elif date_format == 'calendar':
                    group['creation_date'] = parse(metadata['creation_date']).strftime('%B %m %Y')
                else:
                    group['creation_date'] = parse(metadata['creation_date']).strftime(date_format)
                group['role'] = roles.get(group['name'])
                groups.append(group)
        groups.sort(key = lambda group : group['name'])
        return groups
    return None

def get_group_info(group_name, **options):
    response = requests.get(url + '/v1alpha1/groups/' + group_name, params={'token': token})
    data = response.json()
    if data.get('kind') == 'Error':
        logger.error(data['message'])
        raise ConnectApiError(data['message'])
    if data.get('kind') == 'Group':
        group = {}
        metadata = data['metadata']
        group['name'] = metadata['name']
        group['display_name'] = metadata['display_name']
        group['description'] = metadata['description']
        group['email'] = metadata['email']
        group['phone'] = metadata['phone']
        group['purpose'] = metadata['purpose']
        group['unix_id'] = metadata['unix_id']
        group['pending'] = metadata['pending']
        date_format = options.get('date_format', 'calendar')
        if date_format == 'object':
            group['creation_date'] = parse(metadata['creation_date'])
        elif date_format == 'iso':
            group['creation_date'] = parse(metadata['creation_date']).isoformat()
        elif date_format == 'calendar':
            group['creation_date'] = parse(metadata['creation_date']).strftime('%B %m %Y')
        else:
            group['creation_date'] = parse(metadata['creation_date']).strftime(date_format)
        group['is_deletable'] = is_group_deletable(group_name)
        return group
    return None

@decorators.permit_keys('display_name', 'email', 'phone', 'description')
def update_group_info(group_name, **settings):
    request_data = {'apiVersion': 'v1alpha1', 'metadata': settings}
    response = requests.put(url + '/v1alpha1/groups/' + group_name, params={'token': token}, json=request_data)
    if response.text:
        data = response.json()
        if data.get('kind') == 'Error':
            logger.error(data['message'])
            raise ConnectApiError(data['message'])
    logger.info('Updated info for group %s' %group_name)

def update_user_role(username, group_name, role):
    request_data = {'apiVersion': 'v1alpha1', 'group_membership': {'state': role}}
    response = requests.put(url + '/v1alpha1/groups/' + group_name + '/members/' + username, params={'token': token}, json=request_data)
    if response.text:
        data = response.json()
        if data.get('kind') == 'Error':
            logger.error(data['message'])
            raise ConnectApiError(data['message'])
    logger.info('Set role to %s for user %s in group %s' %(role, username, group_name))

def remove_user_from_group(username, group_name):
    response = requests.delete(url + '/v1alpha1/groups/' + group_name + '/members/' + username, params={'token': token})
    if response.text:
        data = response.json()
        if data.get('kind') == 'Error':
            logger.error(data['message'])
            raise ConnectApiError(data['message'])
    logger.info('Removed user %s from group %s' %(username, group_name))

def get_subgroups(group_name):
    response = requests.get(url + '/v1alpha1/groups/' + group_name + '/subgroups', params={'token': token})
    if response.text:
        data = response.json()
        if data.get('kind') == 'Error':
            logger.error(data['message'])
            raise ConnectApiError(data['message'])
        return data.get('groups')
    return None

@decorators.require_keys('name', 'display_name', 'email', 'phone', 'description', 'purpose')
def create_subgroup(group_name, **settings):
    request_data = {'apiVersion': 'v1alpha1', 'metadata': settings}
    response = requests.put(url + '/v1alpha1/groups/' + group_name + '/subgroup_requests/' + settings['name'], params={'token': token}, json=request_data)
    if response.text:
        data = response.json()
        if data.get('kind') == 'Error':
            logger.error(data['message'])
            raise ConnectApiError(data['message'])
    logger.info('Created subgroup %s in group %s' %(settings['name'], group_name))

def is_group_deletable(group_name):
    if group_name in ('root', 'root.atlas-af', 'root.atlas-af.staff', 'root.atlas-af.uchicago', 'root.atlas-ml', 'root.atlas-ml.staff', 'root.iris-hep-ml', 'root.iris-hep-ml.staff', 'root.osg', 'root.osg.login-nodes'):
        return False
    return True

def delete_group(group_name):
    if is_group_deletable(group_name):
        response = requests.delete(url + '/v1alpha1/groups/' + group_name, params={'token': token})
        if response.text:
            data = response.json()
            if data.get('kind') == 'Error':
                logger.error(data['message'])
                raise ConnectApiError(data['message'])
        logger.info('Removed group %s' %group_name)
        return True
    return False