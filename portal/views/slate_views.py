from flask import session, request, render_template, jsonify, redirect, url_for, flash
import requests
from portal import app
from portal.decorators import authenticated
from portal.slate_api import (
    get_app_config,
    get_app_readme,
    list_users_instances_request,
    get_instance_details,
    get_instance_logs,
    delete_instance,
)
from portal.connect_api import get_user_profile, get_user_connect_status
import os
import yaml
from base64 import b64encode
import random

slate_api_token = app.config["SLATE_API_TOKEN"]
slate_api_endpoint = app.config["SLATE_API_ENDPOINT"]
query = {"token": slate_api_token}


def generateToken():
    token_bytes = os.urandom(32)
    b64_encoded = b64encode(token_bytes).decode()
    return b64_encoded


def generateRandomPort():
    """Generate random number between 30000 and 32767 for External Condor Port"""
    random.seed()
    port = random.randrange(30000, 32767)
    print("Now using port: {}".format(port))
    return port


def createTokenSecret(generated_token, user_unix_name):
    # Initialize empty contents dict
    contents = {}
    # Hardcode values while Jupyter-Notebook is the only app being launched
    group = "group_2Q9yPCOLxMg"
    cluster = "uchicago-river-v2"
    secret_name = "{}-jupyter-token".format(user_unix_name)
    key_name = "token"
    key_contents = generated_token
    # Add secret contents key-value to dict
    # for key_name, key_contents in zip (request.form.getlist('key_name'), request.form.getlist('key_contents')):
    #     contents[key_name] = base64.b64encode(key_contents)
    contents[key_name] = key_contents

    add_secret = {
        "apiVersion": "v1alpha3",
        "metadata": {"name": secret_name, "group": group, "cluster": cluster},
        "contents": contents,
    }

    # Add secret to Group
    print("Adding Secret to Group")
    response = requests.post(
        slate_api_endpoint + "/v1alpha3/secrets", params=query, json=add_secret
    )
    print("Response: {}, {}".format(response, response.json()))
    return response


@app.route("/instances", methods=["GET", "POST"])
@authenticated
def view_instances():
    """Connect groups"""
    # query = {"token": slate_api_token, "dev": "true"}
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


@app.route("/instances/<instance_id>", methods=["GET"])
@authenticated
def view_instance(instance_id):
    """View instance details"""
    if request.method == "GET":

        instance_details = get_instance_details(instance_id)
        instance_logs = get_instance_logs(instance_id)
        instance_status = True

        if instance_details["kind"] == "Error":
            instance_status = False
            return render_template("404.html")
        try:
            config = instance_details["metadata"]["configuration"]
            print("Trying to load yaml")
            yaml_config = yaml.load(config, Loader=yaml.FullLoader)
            print("Successfully loaded yaml config")
            token = yaml_config["Jupyter"]["Token"]
        except:
            token = None

        return render_template(
            "instance_profile.html",
            instance_details=instance_details,
            instance_status=instance_status,
            instance_logs=instance_logs,
            token=token,
        )


@app.route("/instances/delete/<instance_id>", methods=["GET"])
@authenticated
def view_delete_instance(instance_id):
    """View instance details"""
    if request.method == "GET":

        deleted_instance_response = delete_instance(instance_id)
        print(deleted_instance_response)

        return redirect(url_for("view_instances"))


@app.route("/instances/deploy", methods=["GET", "POST"])
@authenticated
def create_application():
    """Connect groups"""
    query = {"token": slate_api_token, "dev": "true"}
    if request.method == "GET":
        app_name = "jupyter-notebook"
        profile = get_user_profile(session["unix_name"])
        try:
            public_key = profile["metadata"]["public_key"]
        except:
            public_key = None

        return render_template(
            "instance_create.html", name=app_name, public_key=public_key
        )
    elif request.method == "POST":
        app_name = "jupyter-notebook"

        app_config = get_app_config(app_name)
        app_config = app_config.json()["spec"]["body"]
        # The FullLoader parameter handles the conversion from YAML
        # scalar values to Python the dictionary format
        app_config_yaml = yaml.load(app_config, Loader=yaml.FullLoader)
        # Extract connect group name and replace dot notation with dash for app name format compatibility
        connect_group_name = session["url_host"]["unix_name"].replace(".", "-")
        app_config_yaml["Instance"] = "{}-{}".format(
            session["unix_name"], connect_group_name
        )

        app_config_yaml["Ingress"]["Subdomain"] = "{}-jupyter".format(
            session["unix_name"]
        )
        app_config_yaml["Jupyter"]["NB_USER"] = session["unix_name"]

        # Get user unix ID
        user_profile = get_user_profile(session["unix_name"])
        user_unix_id = user_profile["metadata"]["unix_id"]
        app_config_yaml["Jupyter"]["NB_UID"] = user_unix_id

        # Generate base64 encoded random 32-bytes token
        base64_encoded_token = generateToken()
        app_config_yaml["Jupyter"]["Token"] = base64_encoded_token
        # Set default resource values
        app_config_yaml["Resources"]["Memory"] = 16000
        app_config_yaml["Resources"]["CPU"] = 4000

        app_config_yaml["CondorConfig"]["Enabled"] = True
        app_config_yaml["CondorConfig"]["CollectorHost"] = "flock.opensciencegrid.org"
        app_config_yaml["CondorConfig"]["CollectorPort"] = 9618
        app_config_yaml["CondorConfig"]["IsExternalPool"] = True
        app_config_yaml["CondorConfig"]["ExternalCondorPort"] = generateRandomPort()
        app_config_yaml["CondorConfig"]["AuthTokenSecret"] = "submit-auth-token"
        app_config_yaml["SSH"]["Enabled"] = True

        try:
            # extra_ports_enabled = request.form["extra-ports"]
            low_port = request.form["low-port"]
            high_port = request.form["high-port"]

            app_config_yaml["ExtraPort"]["Enabled"] = True
            app_config_yaml["ExtraPort"]["HighPort"] = low_port
            app_config_yaml["ExtraPort"]["LowPort"] = high_port
            print(
                "Using App Config with Extra Ports: {} - {}".format(low_port, high_port)
            )
        except:
            # extra_ports_enabled = False
            print("Using App Config without Extra Ports")

        try:
            app_config_yaml["SSH"]["SSH_Public_Key"] = request.form["sshpubstring"]
        except:
            profile = get_user_profile(session["unix_name"])
            public_key = profile["metadata"]["public_key"]
            app_config_yaml["SSH"]["SSH_Public_Key"] = public_key
        # Group name: snowmass21-ciconnect
        group = "group_2Q9yPCOLxMg"
        cluster = "uchicago-river-v2"
        configuration = yaml.dump(app_config_yaml)
        # SLATE API: slate app install jupyter-notebook --dev --group <your-group> --cluster <a-cluster> --conf jupyter.conf
        install_app = {
            "apiVersion": "v1alpha3",
            "group": group,
            "cluster": cluster,
            "configuration": configuration,
        }

        # Post query to install application config
        app_install = requests.post(
            slate_api_endpoint + "/v1alpha3/apps/" + app_name,
            params=query,
            json=install_app,
        )
        # print(app_install)
        # print(app_install.json())

        if app_install.status_code == requests.codes.ok:
            flash("Your application has been deployed.", "success")
            return redirect(url_for("view_instances"))
        elif app_install.status_code == 400:
            err_message = app_install.json()["message"]
            flash(
                "Unable to deploy application: You already have a launched instance of this application",
                "warning",
            )
            return redirect(url_for("create_application"))
        else:
            err_message = app_install.json()["message"]
            if "port is not in the valid range" in err_message:
                print("Port was invalid, retrying with new external condor port")
                # Flask code 307 preserve the POST request to retry method
                return redirect(url_for("create_application"), code=307)

        return redirect(url_for("view_instances"))


@app.route("/apps_readme_xhr/<name>", methods=["GET"])
@authenticated
def view_apps_readme_xhr(name):
    app_readme = get_app_readme(name)
    return jsonify(app_readme)


@app.route("/apps_config_ajax/<name>", methods=["GET"])
@authenticated
def apps_config_ajax(name):
    app_config = get_app_config(name)
    return app_config
