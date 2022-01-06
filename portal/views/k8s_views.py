from flask import session, request, render_template, jsonify, redirect, url_for, flash
import requests
from portal import app
from portal.decorators import authenticated
from portal import k8s_api
from portal.connect_api import get_user_profile, get_user_connect_status

@app.route("/jupyter/create", methods=["GET"])
@authenticated
def create_jupyter_notebook():
    app_name = "jupyter-notebook"
    profile = get_user_profile(session["unix_name"])
    try:
        public_key = profile["metadata"]["public_key"]
    except:
        public_key = None

    return render_template("k8s_instance_create.html", name=app_name, public_key=public_key)

@app.route("/jupyter/deploy", methods=["GET", "POST"])
@authenticated
def deploy_jupyter_notebook():
    notebook_name = request.form['notebook-name']
    password = request.form['notebook-password']
    namespace = 'atlas-af-test'
    username = session['unix_name']
    cpu = int(request.form['cpu']) 
    memory = int(request.form['memory']) 
    image = request.form['image']
    time_duration = int(request.form['time-duration'])
    k8s_api.create_jupyter_notebook(notebook_name, namespace, username, password, f"{cpu}", f"{memory}Gi", image, f"{time_duration}")
    return redirect(url_for("view_jupyter_notebooks"))

@app.route("/jupyter/view", methods=["GET"])
@authenticated
def view_jupyter_notebooks():
    namespace = 'atlas-af-test'
    username = session['unix_name']
    notebooks = k8s_api.get_jupyter_notebooks(namespace, username)
    
    profile = get_user_profile(session["unix_name"])
    try:
        public_key = profile["metadata"]["public_key"]
    except:
        public_key = None

    connect_group = session["url_host"]["unix_name"]
    user_status = get_user_connect_status(session["unix_name"], connect_group)

    return render_template(
        "k8s_instances.html",
        name='jupyter_notebook',
        public_key=public_key,
        instances=notebooks,
        user_status=user_status,
    )

@app.route("/jupyter/remove/<namespace>/<notebook_name>", methods=["GET"])
@authenticated
def remove_jupyter_notebook(namespace, notebook_name):
    k8s_api.remove_jupyter_notebook(namespace, notebook_name)
    return redirect(url_for("view_jupyter_notebooks"))