import requests
import json
from flask import session
from dateutil.parser import parse
from datetime import datetime 
from datetime import timedelta
from portal import logger
from portal import app

ciconnect_api_token = app.config["CONNECT_API_TOKEN"]
ciconnect_api_endpoint = app.config["CONNECT_API_ENDPOINT"]
mailgun_api_token = app.config["MAILGUN_API_TOKEN"]
params = {'token': ciconnect_api_token}

def authorized():
    return session.get('admin') == 'admin'

def get_usernames(group):
    if authorized():
        try:
            url = ciconnect_api_endpoint + "/v1alpha1/groups/" + group + "/members?token=" + ciconnect_api_token
            users = requests.get(url).json()
            return [member['user_name']for member in users['memberships']]
        except:
            logger.error('Error getting usernames')

def get_user_profiles(group):
    if authorized():
        try:
            usernames = get_usernames(group)

            multiplex_json = {}
            for username in usernames:
                multiplex_json['/v1alpha1/users/' + username + '?token=' + ciconnect_api_token] = {'method': 'GET'}

            url = ciconnect_api_endpoint + '/v1alpha1/multiplex'
            resp = requests.post(url, params=params, json=multiplex_json)
            data = resp.json()

            profiles = []
            for entry in data:
                user = json.loads(data[entry]['body'])
                username = user['metadata']['unix_name']
                email = user['metadata']['email']
                join_date = parse(user['metadata']['join_date']).strftime('%Y-%m-%d')
                institution = user['metadata']['institution']
                profiles.append({'username': username, 'email': email, 'join_date': join_date, 'institution': institution})
            return profiles
        except:
            logger.error('Error getting user profiles')

def get_email_list(group):
    if authorized():
        email_list = []
        profiles = get_user_profiles(group)
        for profile in profiles:
            email_list.append(profile['email'])
        return email_list

def update_user_institution(username, institution):
    if authorized():
        try:
            json_data = {'apiVersion': 'v1alpha1', 'kind': 'User', 'metadata': {'institution': institution}}
            url = ciconnect_api_endpoint + "/v1alpha1/users/" + username
            resp = requests.put(url, params=params, json=json_data)
            logger.info("Updated user %s. Set institution to %s." %(username, institution))
            return resp
        except Exception as err:
            logger.error("Error updating institution for user %s." %username)
    
def email_users(sender, recipients, subject, body):
    if authorized():
        try: 
            logger.info("Sending email...")
            resp = requests.post("https://api.mailgun.net/v3/api.ci-connect.net/messages",
                auth=("api", mailgun_api_token),
                data={
                    "from": "<" + sender + ">",
                    "to": [sender],
                    "bcc": recipients,
                    "subject": subject,
                    "text": body
                }
            )
            logger.info("Response status: " + resp.status_code)
            logger.info("Response text: " + resp.text)
            return resp
        except:
            logger.error("Error sending email to all users")

