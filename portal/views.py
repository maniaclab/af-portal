""" 
A module for all of the view functions.

The phrase "view function" gets its name from the Model-View-Template (MVT) design pattern. 
A view function is a request handler that returns a view.

The view functions in this module are often preceded by an @app.route decorator.

The @app.route decorator maps a URL to a view function (request handler).
The @app.route decorator also gives the view function access to the request and response objects in the decorator's namespace.

For more documentation on decorators and the @app.route decorator, see decorators.py
"""

from flask import session, request, render_template, url_for, redirect, jsonify, flash
from flask_qrcode import QRcode
from portal import app, connect, jupyterlab, email, math, decorators, logger
from portal.errors import ConnectApiError
from urllib.parse import urlparse, urljoin
import globus_sdk
import threading

QRcode(app)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/chat")
@decorators.login_required
def chat():
    unix_name = session.get("unix_name")
    return render_template("chat.html", unix_name=unix_name)


@app.route("/hardware")
def hardware():
    return render_template("hardware.html")


@app.route("/hardware/gpus")
def get_gpus():
    gpus = jupyterlab.get_gpu_availability()
    return jsonify(gpus=gpus)


@app.route("/signup")
def signup():
    return render_template("signup.html")


@app.route("/login")
def login():
    redirect_uri = url_for("login", _external=True)
    logger.info("redirect_uri", redirect_uri)
    redirect_uri = 'https://test.af.uchicago.edu/login'
    client = globus_sdk.ConfidentialAppAuthClient(
        app.config["CLIENT_ID"], app.config["CLIENT_SECRET"]
    )
    client.oauth2_start_flow(redirect_uri, refresh_tokens=True)
    if "code" not in request.args:
        next_url = get_safe_redirect()
        params = {"signup": 1} if request.args.get("signup") else {"next": next_url}
        auth_uri = client.oauth2_get_authorize_url(additional_params=params)
        return redirect(auth_uri)
    else:
        code = request.args.get("code")
        tokens = client.oauth2_exchange_code_for_tokens(code)
        logger.info("tokens:", tokens)
        id_token = tokens.decode_id_token(client)
        session.update(
            tokens=tokens.by_resource_server,
            is_authenticated=True,
            name=id_token.get("name", ""),
            email=id_token.get("email", ""),
            institution=id_token.get("organization", ""),
            globus_id=id_token.get("sub", ""),
            last_authentication=id_token.get("last_authentication", -1),
        )
        username = connect.get_username(session["globus_id"])
        if username:
            profile = connect.get_user_profile(username)
            if profile:
                session["unix_name"] = profile["unix_name"]
                session["unix_id"] = profile["unix_id"]
                session["role"] = profile["role"]
            else:
                session["role"] = "nonmember"
            return redirect(url_for("home"))
        # Username not found, so try to create a new profile
        else:
            return redirect(url_for("create_profile"))


@app.route("/logout")
@decorators.login_required
def logout():
    client = globus_sdk.ConfidentialAppAuthClient(
        app.config["CLIENT_ID"], app.config["CLIENT_SECRET"]
    )
    for token in (
        token_info["access_token"] for token_info in session["tokens"].values()
    ):
        client.oauth2_revoke_token(token)
    session.clear()
    return redirect(url_for("home"))


def is_safe_redirect_url(target):
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return (
        redirect_url.scheme in ("http", "https")
        and host_url.netloc == redirect_url.netloc
    )


def get_safe_redirect():
    url = request.args.get("next")
    if url and is_safe_redirect_url(url):
        return url
    url = request.referrer
    if url and is_safe_redirect_url(url):
        return url
    return "/"


@app.route("/profile")
@decorators.login_required
def profile():
    unix_name = session.get("unix_name")
    if unix_name:
        profile = connect.get_user_profile(unix_name)
        # The auth string should never get used if the totp_secret key doesn't exist anyhow.
        try:
            issuer = "CI Connect"
            authenticator_string = (
                "otpauth://totp/"
                + unix_name
                + "?secret="
                + profile["totp_secret"]
                + "&issuer="
                + issuer
            )
        except KeyError as e:
            print("Could not create an authenticator string: ", e)
            authenticator_string = None
    return render_template(
        "profile.html", profile=profile, authenticator_string=authenticator_string
    )


@app.route("/profile/create", methods=["GET", "POST"])
@decorators.login_required
def create_profile():
    try:
        if request.method == "GET":
            return render_template("create_profile.html")
        if request.method == "POST":
            profile = {
                "globus_id": session["globus_id"],
                "unix_name": request.form["unix_name"].strip(),
                "name": request.form["name"].strip(),
                "email": request.form["email"].strip(),
                "phone": request.form["phone"].strip(),
                "institution": request.form["institution"].strip(),
                "public_key": request.form["public_key"].strip(),
            }
            connect.create_user_profile(**profile)
            connect.update_user_role(profile["unix_name"], "root.atlas-af", "pending")
            session.update(
                unix_name=profile["unix_name"],
                name=profile["name"],
                phone=profile["phone"],
                email=profile["email"],
                institution=profile["institution"],
            )
            flash("Successfully created profile", "success")
            return redirect(url_for("profile"))
    except ConnectApiError as err:
        flash(str(err), "warning")
        return redirect(url_for("create_profile"))


@app.route("/profile/edit", methods=["GET", "POST"])
@decorators.login_required
def edit_profile():
    unix_name = session["unix_name"]
    try:
        if request.method == "GET":
            profile = connect.get_user_profile(unix_name)
            return render_template("edit_profile.html", profile=profile)
        if request.method == "POST":
            profile = {
                "name": request.form["name"].strip(),
                "email": request.form["email"].strip(),
                "phone": request.form["phone"].strip(),
                "institution": request.form["institution"].strip(),
                "public_key": request.form["public_key"].strip(),
            }
            if request.form.get("totpsecret") is not None:
                profile["create_totp_secret"] = True
            connect.update_user_profile(unix_name, **profile)
            flash("Successfully updated profile", "success")
            return redirect(url_for("profile"))
    except ConnectApiError as err:
        flash(str(err), "warning")
        return redirect(url_for("edit_profile"))


@app.route("/profile/groups")
@decorators.login_required
def user_groups():
    return render_template("user_groups.html")


@app.route("/profile/get_user_groups")
@decorators.login_required
def get_user_groups():
    unix_name = session["unix_name"]
    groups = connect.get_user_groups(unix_name, pattern="root.atlas-af")
    return jsonify(groups=groups)


@app.route("/profile/request_membership/<unix_name>")
@decorators.login_required
def request_membership(unix_name):
    try:
        connect.update_user_role(unix_name, "root.atlas-af", "pending")
        flash("Requested membership in the ATLAS Analysis Facility group", "success")
        return redirect(url_for("profile"))
    except ConnectApiError as err:
        flash(str(err), "warning")
        return redirect(url_for("profile"))


@app.route("/aup")
def aup():
    return render_template("aup.html")


@app.route("/jupyterlab")
@decorators.members_only
def open_jupyterlab():
    return render_template("jupyterlab.html")


@app.route("/jupyterlab/get_notebooks")
@decorators.members_only
def get_notebooks():
    username = session["unix_name"]
    notebooks = jupyterlab.get_notebooks(owner=username, url=True)
    return jsonify(notebooks=notebooks)


@app.route("/jupyterlab/configure")
@decorators.members_only
def configure_notebook():
    username = session["unix_name"]
    notebook_name = jupyterlab.generate_notebook_name(username)
    return render_template("jupyterlab_form.html", notebook_name=notebook_name)


@app.route("/jupyterlab/deploy", methods=["POST"])
@decorators.members_only
@decorators.validate_notebook
def deploy_notebook():
    settings = {
        "notebook_name": request.form["notebook-name"].strip(),
        "notebook_id": request.form["notebook-name"].strip().lower(),
        "image": request.form["image"],
        "owner": session.get("unix_name"),
        "owner_uid": session.get("unix_id"),
        "globus_id": session.get("globus_id"),
        "cpu_request": int(request.form["cpu"]),
        "cpu_limit": int(request.form["cpu"]) * 2,
        "memory_request": "{}Gi".format(int(request.form["memory"])),
        "memory_limit": "{}Gi".format(int(request.form["memory"]) * 2),
        "gpu_request": int(request.form["gpu"]),
        "gpu_limit": int(request.form["gpu"]),
        "gpu_product": request.form["gpu-product"],
        "hours_remaining": int(request.form["duration"]),
    }
    jupyterlab.deploy_notebook(**settings)
    return redirect(url_for("open_jupyterlab"))


@app.route("/jupyterlab/remove/<notebook>")
@decorators.members_only
def remove_notebook(notebook):
    pod = jupyterlab.get_pod(notebook)
    if pod and pod.metadata.labels["owner"] == session["unix_name"]:
        if jupyterlab.remove_notebook(notebook):
            return jsonify(success=True, message="Notebook %s was deleted." % notebook)
    return jsonify(success=False, message="Unable to delete notebook %s" % notebook)


@app.route("/monitoring/login_nodes")
@decorators.members_only
def login_nodes():
    return render_template("login_nodes.html")


@app.route("/monitoring/notebooks")
@decorators.members_only
def notebooks_user():
    username = session["unix_name"]
    notebooks = jupyterlab.get_notebooks(username)
    return render_template("notebooks_user.html", notebooks=notebooks)


@app.route("/monitoring/job_queue")
@decorators.members_only
def job_queue():
    return render_template("job_queue.html")


@app.route("/monitoring/htcondor_usage")
@decorators.members_only
def htcondor_usage():
    return render_template("htcondor_usage.html")


@app.route("/admin/notebooks")
@decorators.admins_only
def notebooks_admin():
    return render_template("notebooks_admin.html")


@app.route("/admin/list_notebooks")
@decorators.admins_only
def list_notebooks():
    notebooks = jupyterlab.list_notebooks()
    return jsonify(notebooks=notebooks)


@app.route("/admin/get_notebook/<notebook_name>")
@decorators.admins_only
def get_notebook(notebook_name):
    notebook = jupyterlab.get_notebook(name=notebook_name, log=True)
    return jsonify(notebook=notebook)


@app.route("/admin/users")
@decorators.admins_only
def user_info():
    return render_template("users.html")


@app.route("/admin/get_user_spreadsheet")
@decorators.admins_only
def get_user_spreadsheet():
    users = connect.get_user_profiles("root.atlas-af", date_format="%m/%d/%Y")
    return jsonify(
        [
            {
                "unix_name": user["unix_name"],
                "name": user["name"],
                "email": user["email"],
                "join_date": user["join_date"],
                "institution": user["institution"],
            }
            for user in users
        ]
    )


@app.route("/admin/update_user_institution", methods=["POST"])
@decorators.admins_only
def update_user_institution():
    username = request.form["username"]
    institution = request.form["institution"]
    connect.update_user_profile(username, institution=institution)
    return jsonify(success=True)


@app.route("/admin/plot_users_over_time")
@decorators.admins_only
def plot_users_over_time():
    data = math.plot_users_over_time()
    return render_template("plot_users_over_time.html", base64_encoded_image=data)


@app.route("/admin/groups/<group_name>")
@decorators.admins_only
def groups(group_name):
    group = connect.get_group_info(group_name)
    return render_template("groups.html", group=group)


@app.route("/admin/get_members/<group_name>")
@decorators.admins_only
def get_members(group_name):
    profiles = connect.get_user_profiles(group_name)
    members = list(
        filter(lambda profile: profile["role"] in ("active", "admin"), profiles)
    )
    return jsonify(members=members)


@app.route("/admin/get_member_requests/<group_name>")
@decorators.admins_only
def get_member_requests(group_name):
    profiles = connect.get_user_profiles(group_name)
    member_requests = list(
        filter(lambda profile: profile["role"] == "pending", profiles)
    )
    return jsonify(member_requests=member_requests)


@app.route("/admin/get_subgroups/<group_name>")
@decorators.admins_only
def get_subgroups(group_name):
    subgroups = connect.get_subgroups(group_name)
    return jsonify(subgroups=subgroups)


@app.route("/admin/get_potential_members/<group_name>")
@decorators.admins_only
def get_potential_members(group_name):
    users = connect.get_user_profiles("root")
    potential_members = list(
        filter(lambda user: user["role"] in ("nonmember", "pending"), users)
    )
    return jsonify(potential_members=potential_members)


@app.route("/admin/email/<group_name>", methods=["POST"])
@decorators.admins_only
def send_email(group_name):
    sender = "noreply@af.uchicago.edu"
    recipients = email.get_email_list(group_name)
    subject = request.form["subject"]
    body = request.form["body"]
    if email.email_users(sender, recipients, subject, body):
        return jsonify(success=True, message="Sent email to group %s" % group_name)
    return jsonify(
        success=False, message="Unable to send email to group %s" % group_name
    )


@app.route("/admin/add_group_member/<group_name>/<unix_name>")
@decorators.admins_only
def add_group_member(unix_name, group_name):
    connect.update_user_role(unix_name, group_name, "active")
    return jsonify(success=True)


@app.route("/admin/remove_group_member/<group_name>/<unix_name>")
@decorators.admins_only
def remove_group_member(unix_name, group_name):
    connect.remove_user_from_group(unix_name, group_name)
    return jsonify(success=True)


@app.route("/admin/approve_membership_request/<group_name>/<unix_name>")
@decorators.admins_only
def approve_membership_request(unix_name, group_name):
    def notify_staff(approver):
        profile = connect.get_user_profile(unix_name)
        subject = "Account approval"
        body = """
            User %s approved a request from %s to join group %s.

            Unix name: %s
            Full name: %s
            Email: %s
            Institution: %s""" % (
            approver,
            unix_name,
            group_name,
            profile["unix_name"],
            profile["name"],
            profile["email"],
            profile["institution"],
        )
        email.email_staff(subject, body)

    connect.update_user_role(unix_name, group_name, "active")
    t = threading.Thread(target=notify_staff, args=(session["unix_name"],))
    t.start()
    return jsonify(success=True)


@app.route("/admin/deny_membership_request/<group_name>/<unix_name>")
@decorators.admins_only
def deny_membership_request(unix_name, group_name):
    connect.remove_user_from_group(unix_name, group_name)
    return jsonify(success=True)


@app.route("/admin/edit_group/<group_name>", methods=["GET", "POST"])
@decorators.admins_only
def edit_group(group_name):
    group = connect.get_group_info(group_name)
    if request.method == "GET":
        return render_template("edit_group.html", group=group)
    elif request.method == "POST":
        try:
            settings = {
                "display_name": request.form["display-name"].strip(),
                "email": request.form["email"].strip(),
                "phone": request.form["phone"].strip(),
                "description": request.form["description"].strip(),
            }
            connect.update_group_info(group_name, **settings)
            flash("Updated group %s successfully" % group_name, "success")
            return redirect(url_for("groups", group_name=group_name))
        except ConnectApiError as err:
            flash(str(err), "warning")
            return redirect(url_for("edit_group", group_name=group_name))


@app.route("/admin/create_subgroup/<group_name>", methods=["GET", "POST"])
@decorators.admins_only
def create_subgroup(group_name):
    if request.method == "GET":
        group = connect.get_group_info(group_name)
        return render_template("create_subgroup.html", group=group)
    elif request.method == "POST":
        settings = {
            "name": request.form["short-name"],
            "display_name": request.form["display-name"],
            "purpose": request.form["purpose"],
            "email": request.form["email"],
            "phone": request.form["phone"],
            "description": request.form["description"],
        }
        connect.create_subgroup(group_name, **settings)
        flash("Created subgroup %s" % settings["name"], "success")
        return redirect(url_for("groups", group_name=group_name))


@app.route("/admin/remove_group/<group_name>")
@decorators.admins_only
def remove_group(group_name):
    connect.remove_group(group_name)
    flash("Removed group %s" % group_name, "success")
    return redirect(url_for("groups", group_name="root.atlas-af"))


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html")


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html")


@app.after_request
def add_cache_control(response):
    response.cache_control.max_age = 0
    return response


@app.before_first_request
def start_notebook_maintenance():
    jupyterlab.start_notebook_maintenance()
