from flask import render_template, request, session
import json

from portal import app
from portal.decorators import authenticated
from portal.connect_api import (
    get_multiplex,
    get_user_connect_status,
    get_user_info,
    get_user_group_memberships,
    get_user_pending_project_requests,
    domain_name_edgecase,
)
import sys

# Read configurable tokens and endpoints from config file, values must be set
ciconnect_api_token = app.config["CONNECT_API_TOKEN"]
ciconnect_api_endpoint = app.config["CONNECT_API_ENDPOINT"]
mailgun_api_token = app.config["MAILGUN_API_TOKEN"]
# Read Brand Dir from config and insert path to read
brand_dir = app.config["MARKDOWN_DIR"]
sys.path.insert(0, brand_dir)


@app.route("/users-groups", methods=["GET"])
@authenticated
def users_groups():
    """Groups that user's are specifically members of"""
    if request.method == "GET":
        query = {"token": ciconnect_api_token, "globus_id": session["primary_identity"]}
        # Get user info to derive unix name
        user = get_user_info(session)
        unix_name = user["metadata"]["unix_name"]
        # Get user's group membership info based on session unix name
        users_group_memberships = get_user_group_memberships(session, unix_name)

        multiplexJson = {}
        group_membership_status = {}
        for group in users_group_memberships:
            if group["state"] not in ["nonmember"]:
                group_name = group["name"]
                group_query = (
                    "/v1alpha1/groups/" + group_name + "?token=" + query["token"]
                )
                multiplexJson[group_query] = {"method": "GET"}
                group_membership_status[group_query] = group["state"]
        # POST request for multiplex return
        multiplex = get_multiplex(multiplexJson)

        users_groups = []
        for group in multiplex:
            if (
                session["url_host"]["unix_name"]
                in (json.loads(multiplex[group]["body"])["metadata"]["name"])
            ) and (
                len(
                    (json.loads(multiplex[group]["body"])["metadata"]["name"]).split(
                        "."
                    )
                )
                > 1
            ):
                users_groups.append(
                    (
                        json.loads(multiplex[group]["body"]),
                        group_membership_status[group],
                    )
                )
        # users_groups = [group for group in users_groups if len(group['name'].split('.')) == 3]

        # Query user's pending project requests
        pending_project_requests = get_user_pending_project_requests(unix_name)
        # Check user's member status of root connect group
        connect_group = session["url_host"]["unix_name"]
        user_status = get_user_connect_status(unix_name, connect_group)

        domain_name = domain_name_edgecase()

        with open(
            brand_dir
            + "/"
            + domain_name
            + "/form_descriptions/group_unix_name_description.md",
            "r",
        ) as file:
            group_unix_name_description = file.read()

        return render_template(
            "users_groups.html",
            groups=users_groups,
            project_requests=pending_project_requests,
            user_status=user_status,
            group_unix_name_description=group_unix_name_description,
        )


@app.route("/users-groups/pending", methods=["GET"])
@authenticated
def users_groups_pending():
    """Groups that user's are specifically members of"""
    if request.method == "GET":
        # query = {"token": ciconnect_api_token, "globus_id": session["primary_identity"]}
        # Get user info
        user = get_user_info(session)
        unix_name = user["metadata"]["unix_name"]

        # Query user's pending project requests
        project_requests = get_user_pending_project_requests(unix_name)
        project_requests = [
            project_request
            for project_request in project_requests
            if session["url_host"]["unix_name"] in project_request["name"]
        ]
        # Check user status of root connect group
        connect_group = session["url_host"]["unix_name"]
        user_status = get_user_connect_status(unix_name, connect_group)
        return render_template(
            "users_groups_pending.html",
            project_requests=project_requests,
            user_status=user_status,
        )
