import requests
import json
from matplotlib.figure import Figure
from io import BytesIO
import base64
from flask import session
from dateutil.parser import parse
from datetime import datetime, timedelta
from portal import app, logger

ciconnect_api_token = app.config["CONNECT_API_TOKEN"]
ciconnect_api_endpoint = app.config["CONNECT_API_ENDPOINT"]
mailgun_api_token = app.config["MAILGUN_API_TOKEN"]
params = {'token': ciconnect_api_token}

def get_usernames(group):
    try:
        url = ciconnect_api_endpoint + "/v1alpha1/groups/" + group + "/members?token=" + ciconnect_api_token
        users = requests.get(url).json()
        return [member['user_name']for member in users['memberships']]
    except:
        logger.error('Error getting usernames')

def get_user_profiles(group):
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
            name = user['metadata']['name']
            profiles.append({'username': username, 'email': email, 'join_date': join_date, 'institution': institution, 'name': name})
        return profiles
    except:
        logger.error('Error getting user profiles')

def get_email_list(group):
    try:
        email_list = []
        profiles = get_user_profiles(group)
        for profile in profiles:
            email_list.append(profile['email'])
    except:
        logger.error('Error getting emails for group %s' %group)
    return email_list

def update_user_institution(username, institution):
    try:
        json_data = {'apiVersion': 'v1alpha1', 'kind': 'User', 'metadata': {'institution': institution}}
        url = ciconnect_api_endpoint + "/v1alpha1/users/" + username
        resp = requests.put(url, params=params, json=json_data)
        logger.info("Updated user %s. Set institution to %s." %(username, institution))
        return resp
    except Exception as err:
        logger.error("Error updating institution for user %s." %username)

def get_email_list(group):
    email_list = []
    profiles = get_user_profiles(group)
    for profile in profiles:
        email_list.append(profile['email'])
    return email_list

def email_users(sender, recipients, subject, body):
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
        return resp
    except:
        logger.error("Error sending email to all users")

def plot_users_by_join_date(users):
    try:
        xvalues_format = "%m-%Y" 
        xvalues_set = set()
        for user in users:
            join_date = datetime.strptime(user['join_date'], '%Y-%m-%d')
            user['jd'] = join_date
            xvalue = datetime(join_date.year, join_date.month, 1).strftime(xvalues_format)
            xvalues_set.add(xvalue)
        xvalues = list(xvalues_set)
        xvalues.sort(key=lambda x:datetime.strptime(x, xvalues_format))
        yvalues = [0] * len(xvalues)
        for i in range(len(xvalues)):
            xvalue = datetime.strptime(xvalues[i], xvalues_format)
            L = list(filter(lambda u : ((xvalue.year - u['jd'].year) * 12) + (xvalue.month - u['jd'].month) >= 0, users))
            yvalues[i] = len(L)
        fig = Figure(figsize=(16, 8), dpi=80, tight_layout=True)
        ax = fig.subplots()
        ax.plot(xvalues, yvalues)
        ax.set_xlabel('Month')
        ax.set_ylabel('Number of users')
        ax.set_title('Number of users by month')
        buf = BytesIO()
        fig.savefig(buf, format='png')
        data = base64.b64encode(buf.getbuffer()).decode("ascii")
        return data
    except:
        logger.error('Error generating user by join date plot')