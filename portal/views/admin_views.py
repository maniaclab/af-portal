from flask import session, request, render_template, jsonify, redirect, url_for, flash
from portal import logger
from portal import app
from portal import admin
from portal.decorators import authenticated
from portal.connect_api import get_user_profile, get_user_connect_status

@app.route("/admin/email", methods=["GET"])
@authenticated
def admin_email():
    return render_template("admin_email.html")

@app.route("/admin/users", methods=["GET"])
@authenticated
def admin_users():
    return render_template("admin_users.html")

@app.route("/admin/user_profiles", methods=["GET"])
@authenticated
def admin_get_user_profiles():
    try:
        user_profiles = admin.get_user_profiles('root.atlas-af')
        return jsonify(user_profiles)
    except:
        return None

@app.route("/admin/update_user_institution", methods=["POST"])
@authenticated
def admin_update_user_institution():
    username = request.form['username']
    institution = request.form['institution']
    status = admin.update_user_institution(username, institution)
    return jsonify(success=status)

@app.route("/admin/email_users", methods=["POST"])
@authenticated
def admin_email_users():
    sender = 'noreply@ci-connect.net'
    # recipients = admin.get_email_list('root.atlas-af')
    recipients = ["rolyata@uchicago.edu"]
    subject = request.form['subject']
    body = request.form['body']
    print("Sender: " + sender)
    print("Recipients: " + str(recipients))
    print("Subject: " + subject)
    print("Body: " + body)
    resp = admin.email_users(sender, recipients, subject, body)
    if resp and resp.status_code == 200:
        flash('Sent email successfully', 'success')
    else:
        flash('Error sending email', 'warning')
    return redirect(url_for('admin_email'))