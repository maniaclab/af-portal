from flask import session, request, render_template, jsonify, redirect, url_for, flash
import requests
from portal import app
from portal.decorators import authenticated
from portal.k8s_api import create_jupyter_notebook

@app.route("/jupyter/deploy", methods=["GET", "POST"])
@authenticated
def deploy_jupyter_notebook():
    create_jupyter_notebook()

    return redirect(url_for("view_instances"))

