from portal import app, auth, logger, connect, jupyterlab, admin
from flask import session, request, render_template, url_for, redirect, jsonify, flash
import globus_sdk
from urllib.parse import urlparse, urljoin
from portal.jupyterlab import JupyterLabException
import time

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/login")
def login():
    try:
        redirect_uri = url_for("login", _external=True)
        client = globus_sdk.ConfidentialAppAuthClient(app.config["CLIENT_ID"], app.config["CLIENT_SECRET"])
        client.oauth2_start_flow(redirect_uri, refresh_tokens=True)
        if "code" not in request.args:
            next_url = get_safe_redirect()
            params = {"signup": 1} if request.args.get("signup") else {"next": next_url}
            auth_uri = client.oauth2_get_authorize_url(additional_params=params)
            return redirect(auth_uri)
        else:
            code = request.args.get("code")
            tokens = client.oauth2_exchange_code_for_tokens(code)
            id_token = tokens.decode_id_token(client)
            session.update(
                tokens=tokens.by_resource_server, 
                is_authenticated=True,
                name=id_token.get("name", ""),
                email=id_token.get("email", ""),
                institution=id_token.get("organization", ""),
                globus_id=id_token.get("sub", ""),
                last_authentication=id_token.get("last_authentication", -1)
            )
            user = connect.find_user(session["globus_id"])
            if user:
                session["unix_name"] = user["unix_name"]
                session["role"] = connect.get_user_role(session["unix_name"])
            return redirect(url_for("home"))
    except Exception as err:
        logger.info(str(err))
        return redirect(url_for("home"))

@app.route("/logout")
@auth.login_required
def logout():
    try:
        client = globus_sdk.ConfidentialAppAuthClient(app.config["CLIENT_ID"], app.config["CLIENT_SECRET"])
        for token in (token_info["access_token"] for token_info in session["tokens"].values()):
            client.oauth2_revoke_token(token)
        session.clear()
        redirect_uri = url_for("home", _external=True)
        globus_logout_url = ("https://auth.globus.org/v2/web/logout?client=%s&redirect_uri=%s&redirect_name=Simple Portal" %(app.config["CLIENT_ID"], redirect_uri))
        return redirect(globus_logout_url)
    except Exception as err:
        logger.info(str(err))
        return redirect(url_for("home"))

def is_safe_redirect_url(target):
  host_url = urlparse(request.host_url)
  redirect_url = urlparse(urljoin(request.host_url, target))
  return redirect_url.scheme in ('http', 'https') and \
    host_url.netloc == redirect_url.netloc

def get_safe_redirect():
  url =  request.args.get('next')
  if url and is_safe_redirect_url(url):
    return url
  url = request.referrer
  if url and is_safe_redirect_url(url):
    return url
  return '/'

@app.route("/profile")
@auth.login_required
def profile():
    try:
        unix_name = session["unix_name"]
        profile = connect.get_user_profile(unix_name)
        return render_template("profile.html", profile=profile)
    except Exception as err:
        logger.info(str(err))
        return render_template("profile.html", profile=None)

@app.route("/profile/edit", methods=["GET", "POST"])
@auth.login_required
def edit_profile():
    try:
        unix_name = session["unix_name"]
        if request.method == "GET":
            profile = connect.get_user_profile(unix_name)
            return render_template("edit_profile.html", profile=profile)
        if request.method == "POST":
            name = request.form["name"]
            phone = request.form["phone"]
            institution = request.form["institution"]
            email = request.form["email"]
            x509_dn = request.form["X.509_DN"]
            public_key = request.form["public_key"]
            connect.update_user_profile(unix_name, name=name, phone=phone, institution=institution, email=email, x509_dn=x509_dn, public_key=public_key)
            return redirect(url_for('profile'))
    except Exception as err:
        logger.info(str(err))
        return redirect(url_for('profile'))

@app.route("/profile/groups")
@auth.login_required
def user_groups():
    try:
        unix_name = session["unix_name"]
        groups = connect.get_user_groups(unix_name)
        return render_template("user_groups.html", groups=groups)
    except Exception as err:
        logger.info(str(err))
        return render_template("user_groups.html", groups=[])

@app.route("/aup")
def aup():
    return render_template("aup.html")

@app.route("/jupyter")
@auth.members_only
def open_jupyterlab():
    try:
        username = session["unix_name"]
        notebooks = jupyterlab.get_notebooks(username)
        return render_template("jupyterlab.html", notebooks=notebooks)
    except JupyterLabException as err:
        flash(str(err), "error")
        return render_template("jupyterlab.html", notebooks=[])

@app.route("/jupyter/configure")
@auth.members_only
def configure_notebook():
    username = session["unix_name"]
    notebook_name = jupyterlab.generate_notebook_name(username)
    return render_template("jupyterlab_form.html", notebook_name=notebook_name)

@app.route("/jupyter/deploy", methods=["POST"])
@auth.members_only
def deploy_notebook():
    try:
        notebook_name = request.form['notebook-name'].strip()
        settings = {
            "globus_id": session["globus_id"],
            "username": session["unix_name"],
            "cpu_request": int(request.form["cpu"]),
            "cpu_limit": int(request.form["cpu"])*2,
            "memory_request": int(request.form['memory']),
            "memory_limit": int(request.form['memory'])*2,  
            "gpu_request": int(request.form['gpu']),
            "gpu_limit": int(request.form['gpu']),
            "gpu_memory": int(request.form['gpu-memory']),
            "image": request.form['image'],
            "duration": int(request.form['duration'])}
        jupyterlab.create_notebook(notebook_name, **settings)
    except JupyterLabException as err:
        flash(str(err), "error")
    return redirect(url_for("open_jupyterlab"))

@app.route("/jupyter/remove/<notebook>")
@auth.members_only
def remove_notebook(notebook):
    try:
        jupyterlab.remove_notebook(notebook)
        return jsonify(success=True)
    except JupyterLabException:
        return jsonify(success=False)

@app.route("/jupyter/notebooks")
@auth.members_only
def get_notebooks():
    try:
        username = session["unix_name"]
        notebooks = jupyterlab.get_notebooks(username)
        return notebooks
    except JupyterLabException:
        return []

@app.route("/admin/plot_users_over_time", methods=["GET"])
@auth.admins_only
def plot_users_over_time():
    try:
        data = admin.plot_users_over_time()
        return render_template("plot_users_over_time.html", base64_encoded_image = data)
    except Exception as err:
        logger.info(str(err))
        return render_template("plot_users_over_time.html", base64_encoded_image = None)

@app.route("/admin/user_info")
@auth.admins_only
def user_info():
    try:
        usernames = connect.get_group_members("root.atlas-af")
        users = connect.get_user_profiles(usernames, date_format="%m/%d/%Y")
        return render_template("user_info.html", users=users)
    except Exception as err:
        logger.info(str(err))
        return render_template("user_info.html", users=[])

@app.route("/admin/update_user_institution", methods=["POST"])
@auth.admins_only
def update_user_institution():
    try:
        username = request.form['username']
        institution = request.form['institution']
        success = connect.update_user_institution(username, institution)
        return jsonify(success)
    except Exception as err:
        logger.info(str(err))
        return jsonify(success=False)

@app.route("/admin/notebook_metrics")
@auth.admins_only
def notebook_metrics():
    try: 
        notebooks = jupyterlab.get_all_notebooks()
        return render_template("notebook_metrics.html", notebooks=notebooks)
    except JupyterLabException as e:
        flash(str(e), 'warning')
        return render_template("notebook_metrics.html", notebooks=[])

@app.route("/monitoring/notebook_metrics")
@auth.members_only
def user_notebook_metrics():
    try: 
        username = session["unix_name"]
        notebooks = jupyterlab.get_notebooks(username)
        return render_template("notebook_metrics_for_user.html", notebooks=notebooks)
    except JupyterLabException as e:
        flash(str(e), 'warning')
        return render_template("notebook_metrics_for_user.html", notebooks=[])

@app.route("/monitoring/login_nodes")
@auth.admins_only
def login_nodes():
    return render_template("login_nodes.html")

@app.route("/groups/<groupname>")
@auth.admins_only
def groups(groupname):
    try:
        start = time.time()
        usernames = connect.get_group_members("root")
        users = connect.get_user_profiles(usernames)
        members = []
        member_requests = []
        nonmembers = []
        for user in users:
            group_membership = list(filter(lambda group : group["name"] == groupname, user["group_memberships"]))
            if not group_membership:
                nonmembers.append(user)
            elif group_membership[0]["state"] == "pending":
                member_requests.append(user)
                nonmembers.append(user)
            elif group_membership[0]["state"] in ("admin", "active"):
                members.append(user)
        subgroups = connect.get_subgroups(groupname)
        subgroup_requests = connect.get_subgroup_requests(groupname)
        group_info = connect.get_group_info(groupname)
        group = {
            "info": group_info,
            "members": members,
            "member_requests": member_requests,
            "subgroups": subgroups,
            "subgroup_requests": subgroup_requests,
            "nonmembers": nonmembers
        }
        stop = time.time()
        logger.info("The groups view function has taken %.2f ms", (stop-start)*1000)
        return render_template("groups.html", group=group)
    except Exception as err:
        logger.error(str(err))
        return render_template("groups.html", group={})

@app.route("/groups/<groupname>/email", methods=["POST"])
@auth.admins_only
def send_email(groupname):
    try:
        sender = "noreply@af.uchicago.edu"
        recipients = admin.get_email_list(groupname)
        subject = request.form["subject"]
        body = request.form["body"]
        success = admin.email_users(sender, recipients, subject, body)
        if success:
            return jsonify(message="Sent email to group %s" %groupname, category="success")
        return jsonify(message="Error sending email to group %s" %groupname, category="warning")
    except Exception as err:
        logger.error(str(err))
        return jsonify(message="Error sending email to group %s" %groupname, category="warning")

@app.route("/groups/<group_name>/add_group_member/<unix_name>")
@auth.admins_only
def add_group_member(unix_name, group_name):
    try:
        success = connect.add_user_to_group(unix_name, group_name)
        profile = connect.get_user_profile(unix_name)
        approver = session["unix_name"]
        subject = "Account approval"
        body = """
            User %s approved a request from %s to join group %s.

            Unix name: %s
            Full name: %s
            Email: %s
            Institution: %s""" %(approver, unix_name, group_name, profile["unix_name"], profile["name"], profile["email"], profile["institution"])
        admin.email_staff(subject, body)
        flash("Added %s to group %s" %(unix_name, group_name), "success")
        return redirect(url_for("groups", groupname=group_name))
    except Exception as err:
        logger.error(str(err))
        flash("Error adding %s to group %s" %(unix_name, group_name), "warning")
        return redirect(url_for("groups", groupname=group_name))

@app.route("/groups/<group_name>/delete_group_member/<unix_name>")
@auth.admins_only
def remove_group_member(unix_name, group_name):
    try:
        success = connect.remove_user_from_group(unix_name, group_name)
        flash("Removed %s from group %s" %(unix_name, group_name), "success")
        return redirect(url_for("groups", groupname=group_name))
    except Exception as err:
        logger.error(str(err))
        flash("Error removing %s from group %s" %(unix_name, group_name), "warning")
        return redirect(url_for("groups", groupname=group_name))

@app.route("/groups/<group_name>/approve_subgroup_request/<subgroup_name>")
@auth.admins_only
def approve_subgroup_request(subgroup_name, group_name):
    try:
        success = connect.approve_subgroup_request(subgroup_name, group_name)
        flash("Approved request for subgroup %s" %subgroup_name, "success")
        return redirect(url_for("groups", groupname=group_name))
    except Exception as err:
        logger.error(str(err))
        flash("Error approving request for subgroup %s" %subgroup_name, "warning")
        return redirect(url_for("groups", groupname=group_name))

@app.route("/groups/<group_name>/deny_subgroup_request/<subgroup_name>")
@auth.admins_only
def deny_subgroup_request(subgroup_name, group_name):
    try:
        success = connect.deny_subgroup_request(subgroup_name, group_name)
        flash("Denied request for subgroup %s" %subgroup_name, "success")
        return redirect(url_for("groups", groupname=group_name))
    except Exception as err:
        logger.error(str(err))
        flash("Error denying request for subgroup %s" %subgroup_name, "warning")
        return redirect(url_for("groups", groupname=group_name))

@app.route("/groups/<group_name>/edit", methods=["GET", "POST"])
@auth.admins_only
def edit_group(group_name):
    try:
        group = connect.get_group_info(group_name)
        if request.method == "GET":
            return render_template("edit_group.html", group=group)
        elif request.method == "POST":
            kwargs = {
                "display_name": request.form["display-name"],
                "email": request.form["email"],
                "phone": request.form["phone"],
                "description": request.form["description"]
            }
            connect.update_group_info(group_name, **kwargs)
            flash("Updated group %s successfully" %group_name, "success")
            return redirect(url_for("groups", groupname=group_name))
    except Exception as err:
        logger.error(str(err))
        flash("Error updating group %s" %group_name, "warning")
        return render_template("edit_group.html", group=None)