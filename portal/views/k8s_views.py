from flask import session, request, render_template, jsonify, redirect, url_for, flash
import requests
from portal import app
from portal.decorators import authenticated
import k8s_api

@app.route("/instances/deploy_jupyter", methods=["GET", "POST"])
@authenticated
def deploy_jupyter():
    create_jupyter_notebook()

    return redirect(url_for("view_instances"))