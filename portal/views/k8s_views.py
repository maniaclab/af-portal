from flask import session, request, render_template, jsonify, redirect, url_for, flash
import requests
from portal import app
from portal.decorators import authenticated
import k8s_api

@app.route("/jupyter/deploy", methods=["GET", "POST"])
@authenticated
def deploy_jupyter_notebook():
    k8s_api.create_jupyter_notebook()

    return redirect(url_for("view_jupyter_notebooks"))

@app.route("/jupyter/view", methods=["GET", "POST"])
@authenticated
def view_jupyter_notebooks():
    """Connect groups"""
    query = {"token": slate_api_token, "dev": "true"}
    if request.method == "GET":
        app_name = "jupyter-notebook"
        profile = get_user_profile(session["unix_name"])
        try:
            public_key = profile["metadata"]["public_key"]
        except:
            public_key = None
        instances = list_users_instances_request(session)

        # Check user's member status of connect group specifically
        connect_group = session["url_host"]["unix_name"]
        user_status = get_user_connect_status(session["unix_name"], connect_group)

        return render_template(
            "instances.html",
            name=app_name,
            public_key=public_key,
            instances=instances,
            user_status=user_status,
        )