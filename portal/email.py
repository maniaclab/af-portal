''' Functions for sending emails from our email accounts. '''
from portal import app, connect
import requests

token = app.config.get('MAILGUN_API_TOKEN')


def email_users(sender, recipients, subject, body):
    app.logger.info('Sending email...')
    resp = requests.post('https://api.mailgun.net/v3/api.ci-connect.net/messages',
                         auth=('api', token),
                         data={
                             'from': '<' + sender + '>',
                             'to': [sender],
                             'bcc': recipients,
                             'subject': subject,
                             'text': body
                         }
                         )
    if resp.status_code == requests.codes.ok:
        app.logger.info('Sent email with subject %s' % subject)
        return True
    app.logger.info('Unable to send email with subject %s' % subject)
    return False


def email_staff(subject, body):
    sender = 'noreply@af.uchicago.edu'
    recipients = get_email_list('root.atlas-af.staff')
    return email_users(sender, recipients, subject, body)


def get_email_list(group):
    profiles = connect.get_user_profiles(group)
    return [profile['email'] for profile in profiles]
