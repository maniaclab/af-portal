from flask import session, request, render_template, jsonify, redirect, url_for, flash
from portal import logger
from portal import app
from portal import admin
from portal.admin import authorized
from portal.decorators import authenticated
from portal.connect_api import get_user_profile, get_user_connect_status
from portal import k8s_api
from portal.k8s_api import k8sException

@app.route("/admin/email", methods=["GET"])
@authenticated
def admin_email():
    if authorized():
        return render_template("admin_email.html")
    return render_template("404.html")

@app.route("/admin/users", methods=["GET"])
@authenticated
def admin_users():
    if authorized(): 
        return render_template("admin_users.html")
    return render_template("404.html")

@app.route("/admin/user_profiles", methods=["GET"])
@authenticated
def admin_get_user_profiles():
    if authorized():
        user_profiles = admin.get_user_profiles('root.atlas-af')
        return jsonify(user_profiles)

@app.route("/admin/update_user_institution", methods=["POST"])
@authenticated
def admin_update_user_institution():
    if authorized():
        username = request.form['username']
        institution = request.form['institution']
        resp = admin.update_user_institution(username, institution)
        return jsonify(success = True if resp and resp.status_code == 200 else False)

@app.route("/admin/email_users", methods=["POST"])
@authenticated
def admin_email_users():
    if authorized():
        sender = 'noreply@ci-connect.net'
        # recipients = admin.get_email_list('root.atlas-af')
        recipients = []
        subject = request.form['subject']
        body = request.form['body']
        resp = admin.email_users(sender, recipients, subject, body)
        if resp and resp.status_code == 200:
            flash('Sent email successfully', 'success')
        else:
            flash('Error sending email', 'warning')
        return redirect(url_for('admin_email'))
    return render_template("404.html")

@app.route("/admin/plot_users_by_join_date", methods=["GET"])
@authenticated
def plot_users_by_join_date():
    if authorized(): 
        users = admin.get_user_profiles('root.atlas-af')
        data = admin.plot_users_by_join_date(users)
        return render_template("admin_plot_users_by_join_date.html", base64_encoded_image = data)
    return render_template("404.html")

@app.route("/admin/all_notebooks", methods=["GET"])
@authenticated
def all_notebooks_admin():
    if authorized():
        try: 
            notebooks = k8s_api.get_all_notebooks()
            return render_template("admin_all_notebooks.html", notebooks=notebooks)
        except k8sException as e:
            flash(str(e), 'warning')
        except:
            flash('Error getting Jupyter notebooks', 'warning')
        return render_template("admin_all_notebooks.html", notebooks=[])
    return render_template("404.html")