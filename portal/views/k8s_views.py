from flask import session, request, render_template, jsonify, redirect, url_for, flash
import requests
from portal import logger
from portal import app
from portal import k8s_api
from portal.k8s_api import k8sException
from portal.decorators import authenticated
from portal.connect_api import get_user_profile, get_user_connect_status

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
    try:
        globus_id = session['primary_identity']
        notebook_name = request.form['notebook-name'].strip()
        username = session['unix_name']
        cpu = int(request.form['cpu']) 
        memory = int(request.form['memory']) 
        gpu = int(request.form['gpu'])
        image = request.form['image']
        time_duration = int(request.form['time-duration'])
        k8s_api.create_notebook(notebook_name, username, globus_id, cpu, memory, gpu, image, time_duration)
    except k8sException as e:
        flash(str(e), 'warning')
    except:
        flash('Error creating Jupyter notebook %s' %notebook_name, 'warning')
    return redirect(url_for("view_jupyter_notebooks"))

def needs_refresh(notebooks):
    for notebook in notebooks:
        if notebook['notebook_status'] != 'Ready' or notebook['pod_status'] != 'Running' or notebook['cert_status'] != 'Ready': 
            return True
    return False

@app.route("/jupyter/view", methods=["GET"])
@authenticated
def view_jupyter_notebooks():
    try:
        username = session['unix_name']
        notebooks = k8s_api.get_notebooks(username)
        refresh = needs_refresh(notebooks)
        logger.info("refresh = %s" %refresh)
        return render_template("k8s_instances.html", instances=notebooks, refresh=refresh)
    except k8sException as e:
        flash(str(e), 'warning')
    except:
        flash('Error getting Jupyter notebooks', 'warning')
    logger.info('Rendering template k8s_instance.html with refresh=%s' %refresh)
    return render_template("k8s_instances.html", instances=[], refresh=False)

@app.route("/jupyter/remove/<notebook_name>", methods=["GET"])
@authenticated
def remove_jupyter_notebook(notebook_name):
    try:
        username = session['unix_name']
        k8s_api.remove_user_notebook(notebook_name, username)
    except k8sException as e:
        flash(str(e), 'warning')
    except:
        flash('Error removing notebook %s' %notebook_name, 'warning')
    return redirect(url_for("view_jupyter_notebooks"))