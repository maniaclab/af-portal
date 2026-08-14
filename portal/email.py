"""Functions for sending emails from our email accounts."""

import requests

from portal import connect
from portal.app import app, logger

token = app.config.get("MAILGUN_API_TOKEN")


def email_users(sender, recipients, subject, body):
    logger.info("Sending email...")
    resp = requests.post(
        "https://api.mailgun.net/v3/api.ci-connect.net/messages",
        auth=("api", token),
        data={
            "from": "<" + sender + ">",
            "to": [sender],
            "bcc": recipients,
            "subject": subject,
            "text": body,
        },
    )
    if resp.status_code == requests.codes.ok:
        logger.info(f"Sent email with subject {subject}")
        return True
    logger.info(f"Unable to send email with subject {subject}")
    return False


def email_staff(subject, body):
    sender = "noreply@af.uchicago.edu"
    # recipients = get_email_list('root.atlas-af.staff')
    recipients = ["atlas-us-chicago-tier3-admins@lists.uchicago.edu"]
    return email_users(sender, recipients, subject, body)


def get_email_list(group):
    profiles = connect.get_user_profiles(group)
    return [profile["email"] for profile in profiles]
