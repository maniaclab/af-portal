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
    try:
        resp = k8s_api.create_notebook(notebook_name, namespace, username, password, f"{cpu}", f"{memory}Gi", image, f"{time_duration}")
        flash(resp['message'], resp['status'])
    except:
        logger.info('Error creating Jupyter notebook')
        flash('Error creating Jupyter notebook %s in namespace %s' %(notebook_name, namespace), 'warning')
    return redirect(url_for("view_jupyter_notebooks"))

@app.route("/jupyter/view", methods=["GET"])
@authenticated
def view_jupyter_notebooks():
    refresh = False
    namespace = 'atlas-af-test'
    username = session['unix_name']
    try:
        notebooks = k8s_api.get_notebooks(namespace, username)
    except:
        logger.info('Error getting Jupyter notebooks')

    for notebook in notebooks:
        if notebook['notebook_status'] != 'Ready': 
            refresh = True
            break

    logger.info('Rendering template k8s_instance.html with refresh=%s' %refresh)
    return render_template("k8s_instances.html", instances=notebooks, refresh=refresh)

@app.route("/jupyter/remove/<namespace>/<notebook_name>", methods=["GET"])
@authenticated
def remove_jupyter_notebook(namespace, notebook_name):
    username = session['unix_name']
    try:
        resp = k8s_api.remove_user_notebook(namespace, notebook_name, username)
        flash(resp['message'], resp['status'])
    except:
        logger.info('Error removing Jupyter notebook')
        flash('Error removing notebook %s in namespace %s' %(notebook_name, namespace), 'warning')
    return redirect(url_for("view_jupyter_notebooks"))