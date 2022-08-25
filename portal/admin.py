import base64
from matplotlib.figure import Figure
from io import BytesIO
from datetime import datetime
import pandas as pd
from portal import app, logger, connect
import requests

def plot_users_over_time():
    usernames = connect.get_group_members("root.atlas-af")
    users = connect.get_user_profiles(usernames, date_format=None)
    datemin = datetime(2021, 7, 1)
    datemax = datetime.today()
    dates = pd.date_range(datemin, datemax, freq="MS").to_pydatetime().tolist()
    xvalues = list(map(lambda d : d.strftime("%m-%Y"), dates))
    yvalues = [0] * len(xvalues)
    for i in range(len(dates)):
        year = dates[i].year
        month = dates[i].month
        L = list(filter(lambda u : u["join_date"].year < year or (u["join_date"].year == year and u["join_date"].month <= month), users))
        yvalues[i] = len(L)
    fig = Figure(figsize=(16, 8), dpi=80, tight_layout=True)
    ax = fig.subplots()
    ax.plot(xvalues, yvalues)
    ax.set_xlabel("Month")
    ax.set_ylabel("Number of users")
    buf = BytesIO()
    fig.savefig(buf, format="png")
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return data

def get_email_list(group):
    group_members = connect.get_group_members(group)
    profiles = connect.get_user_profiles(group_members)
    email_list = [profile["email"] for profile in profiles]
    return email_list

def email_users(sender, recipients, subject, body):
    logger.info("Sending email...")
    resp = requests.post("https://api.mailgun.net/v3/api.ci-connect.net/messages",
        auth=("api", app.config.get("MAILGUN_API_TOKEN")),
        data={
            "from": "<" + sender + ">",
            "to": [sender],
            "bcc": recipients,
            "subject": subject,
            "text": body
        }
    )
    if resp and resp.status_code == 200:
        logger.info("Sent email with subject %s" %subject)
        return True
    return False

def email_staff(subject, body):
    sender = "noreply@af.uchicago.edu"
    recipients = get_email_list("root.atlas-af.staff")
    return email_users(sender, recipients, subject, body)