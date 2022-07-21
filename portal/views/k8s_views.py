from flask import session, request, render_template, jsonify, redirect, url_for, flash
import requests
from portal import logger, app, k8s_api
from portal.k8s_api import k8sException
from portal.decorators import site_member
from portal.connect_api import get_user_profile, get_user_connect_status

@app.route("/jupyter/create", methods=["GET"])
@site_member
def create_jupyter_notebook():
    try:
        username = session['unix_name']
        nbname = k8s_api.get_autogenerated_notebook_name(username)
        return render_template("k8s_instance_create.html", autogen_nbname=nbname)
    except:
        logger.error('Error getting autogenerated notebook name')    
    return render_template("500.html")

@app.route("/jupyter/deploy", methods=["GET", "POST"])
@site_member
def deploy_jupyter_notebook():
    try:
        globus_id = session['primary_identity']
        notebook_name = request.form['notebook-name'].strip()
        username = session['unix_name']
        cpu = int(request.form['cpu']) 
        memory = int(request.form['memory']) 
        gpu = int(request.form['gpu'])
        gpu_memory = int(request.form['gpu-memory'])
        image = request.form['image']
        time_duration = int(request.form['time-duration'])
        k8s_api.create_notebook(notebook_name, username, globus_id, cpu, memory, gpu, gpu_memory, image, time_duration)
        return redirect(url_for("view_jupyter_notebooks"))
    except k8sException as e:
        flash(str(e), 'warning')
    except:
        flash('Error creating Jupyter notebook %s' %notebook_name, 'warning')
    return render_template("500.html")

def needs_refresh(notebooks):
    for notebook in notebooks:
        if notebook['notebook_status'] != 'Ready' or notebook['pod_status'] != 'Running' or notebook['cert_status'] != 'Ready': 
            return True
    return False

@app.route("/jupyter/view", methods=["GET"])
@site_member
def view_jupyter_notebooks():
    try:
        username = session['unix_name']
        notebooks = k8s_api.get_notebooks(username)
        return render_template("k8s_instances.html", instances=notebooks)
    except k8sException as e:
        flash(str(e), 'warning')
    except:
        flash('Error getting Jupyter notebooks', 'warning')
    return render_template("500.html")

@app.route("/jupyter/remove/<notebook_name>", methods=["GET"])
@site_member
def remove_jupyter_notebook(notebook_name):
    try:
        username = session['unix_name']
        k8s_api.remove_user_notebook(notebook_name, username)
        return redirect(url_for("view_jupyter_notebooks"))
    except k8sException as e:
        flash(str(e), 'warning')
    except:
        flash('Error removing notebook %s' %notebook_name, 'warning')
    return render_template("500.html")

@app.route("/jupyter/remove/<notebook_name>", methods=["POST"])
@site_member
def remove_jupyter_notebook_post(notebook_name):
    try:
        username = session['unix_name']
        k8s_api.remove_user_notebook(notebook_name, username)
        return jsonify(success=True)
    except:
        logger.error('Error removing notebook %s' %notebook_name)
        return jsonify(success=False)

@app.route("/jupyter/status/<notebook>", methods=["GET"])
@site_member
def get_notebook_status(notebook):
    try:
        username = session['unix_name']
        pod = k8s_api.get_pod(notebook)
        if not pod:
            return jsonify(notebook_status=False)
        if pod.metadata.labels['owner'] != username:
            logger.error('Pod %s is not owned by user %s' %(notebook, username))
            return jsonify(notebook_status=False)
        notebook_status = k8s_api.get_notebook_status(pod)
        detailed_status = k8s_api.get_detailed_notebook_status(pod)
        return jsonify(notebook_status=notebook_status, detailed_status=detailed_status)
    except:
        errorMsg = 'Error getting notebook status for notebook %s' %notebook
        logger.error(errorMsg)
        return jsonify(notebook_status=False, error=errorMsg)