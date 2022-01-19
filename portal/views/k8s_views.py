from flask import session, request, render_template, jsonify, redirect, url_for, flash
import requests
from portal.decorators import authenticated
from portal.connect_api import get_user_profile, get_user_connect_status
from portal import logger
from portal import app
from portal import k8s_api

@app.route("/jupyter/create", methods=["GET"])
@authenticated
def create_jupyter_notebook():
    try:
        profile = get_user_profile(session["unix_name"])
        public_key = profile["metadata"]["public_key"]
    except:
        public_key = None

    return render_template("k8s_instance_create.html", public_key=public_key)

def strip(str):
    if str:
        return str.strip()
    return str

@app.route("/jupyter/deploy", methods=["GET", "POST"])
@authenticated
def deploy_jupyter_notebook():
    try:
        notebook_name = strip(request.form['notebook-name'])
        password = strip(request.form['notebook-password'])
        username = session['unix_name']
        cpu = int(request.form['cpu']) 
        memory = int(request.form['memory']) 
        gpu = int(request.form['gpu'])
        image = request.form['image']
        time_duration = int(request.form['time-duration'])
        resp = k8s_api.create_notebook(notebook_name, username, password, f"{cpu}", f"{memory}Gi", f"{gpu}", image, f"{time_duration}")
        flash(resp['message'], resp['status'])
    except:
        logger.error('Error creating Jupyter notebook')
        flash('Error creating Jupyter notebook %s' %notebook_name, 'warning')
    return redirect(url_for("view_jupyter_notebooks"))

@app.route("/jupyter/view", methods=["GET"])
@authenticated
def view_jupyter_notebooks():
    refresh = False
    try:
        username = session['unix_name']
        notebooks = k8s_api.get_notebooks(username)
        for notebook in notebooks:
            if notebook['notebook_status'] != 'Ready' or notebook['pod_status'] != 'Running' or notebook['cert_status'] != 'Ready': 
                refresh = True
                break
    except:
        logger.error('Error getting Jupyter notebooks')

    logger.info('Rendering template k8s_instance.html with refresh=%s' %refresh)
    return render_template("k8s_instances.html", instances=notebooks, refresh=refresh)

@app.route("/jupyter/remove/<notebook_name>", methods=["GET"])
@authenticated
def remove_jupyter_notebook(notebook_name):
    try:
        username = session['unix_name']
        resp = k8s_api.remove_user_notebook(notebook_name, username)
        flash(resp['message'], resp['status'])
    except:
        logger.error('Error removing Jupyter notebook')
        flash('Error removing notebook %s' %notebook_name, 'warning')

    return redirect(url_for("view_jupyter_notebooks"))