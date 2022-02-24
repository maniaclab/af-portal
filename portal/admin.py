import requests
from flask import session
from dateutil.parser import parse
from datetime import datetime 
from datetime import timedelta
from portal import logger
from portal import app

ciconnect_api_token = app.config["CONNECT_API_TOKEN"]
ciconnect_api_endpoint = app.config["CONNECT_API_ENDPOINT"]
mailgun_api_token = app.config["MAILGUN_API_TOKEN"]

def authorized():
    return session.get('admin') == 'admin'

def get_users(group):
    if authorized():
        url = ciconnect_api_endpoint + "/v1alpha1/groups/" + group + "/members?token=" + ciconnect_api_token
        users = requests.get(url).json()
        return users

def get_user_profile(username):
    if authorized():
        url = ciconnect_api_endpoint + "/v1alpha1/users/" + username + "?token=" + ciconnect_api_token
        user_profile = requests.get(url).json()
        return user_profile

def get_user_profiles(group):
    if authorized():
        user_list = []
        users = get_users(group)

        for member in users['memberships']:
            username = member['user_name']
            user_profile = get_user_profile(username)
            username = user_profile['metadata']['unix_name'] 
            join_date = parse(user_profile['metadata']['join_date']).strftime('%Y-%m-%d')
            email = user_profile['metadata']['email']
            institution = user_profile['metadata']['institution']
            name = user_profile['metadata']['name']
            phone = user_profile['metadata']['phone']
            user_entry = {
                'username': username, 
                'email': email, 
                'institution': institution,
                'join_date': join_date,
            }
            user_list.append(user_entry)
        return user_list

def get_email_list(group):
    if authorized():
        email_list = []
        report = get_user_profiles(group)
        for user in report:
            email_list.append(user['email'])
        return email_list

def update_user_institution(username, institution):
    if authorized():
        query = {"token": ciconnect_api_token}
        json_data = {'apiVersion': 'v1alpha1', 'kind': 'User', 'metadata': {'institution': institution}}
        url = ciconnect_api_endpoint + "/v1alpha1/users/" + username
        try:
            requests.put(url, params=query, json=json_data)
            logger.info("Updated user %s. Set institution to %s." %(username, institution))
            return True
        except Exception as err:
            logger.error("Error updating institution for user %s." %username)
            return False
    
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

