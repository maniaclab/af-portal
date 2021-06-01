from flask import flash, redirect, render_template, request, session, url_for, jsonify
import requests
import json

from portal import app
from portal.decorators import authenticated
from portal.connect_api import (
    get_user_info,
    get_multiplex,
    get_user_connect_status,
    get_subgroups,
    get_group_info,
    get_group_members,
    get_user_group_status,
    get_enclosing_group_status,
    update_user_group_status,
    domain_name_edgecase,
    get_group_members_emails,
)
import sys

# Read configurable tokens and endpoints from config file, values must be set
ciconnect_api_token = app.config["CONNECT_API_TOKEN"]
ciconnect_api_endpoint = app.config["CONNECT_API_ENDPOINT"]
mailgun_api_token = app.config["MAILGUN_API_TOKEN"]
# Read Brand Dir from config and insert path to read
brand_dir = app.config["MARKDOWN_DIR"]
sys.path.insert(0, brand_dir)


@app.route("/groups", methods=["GET"])
@authenticated
def groups():
    """Connect groups"""
    if request.method == "GET":
        connect_group = session["url_host"]["unix_name"]
        # Get group's subgroups information
        groups = get_subgroups(connect_group, session)
        # Filter subgroups directly one level nested under group
        group_index = len(connect_group.split("."))
        groups = [
            group
            for group in groups
            if (
                len(group["name"].split(".")) == (group_index + 1)
                and not group["pending"]
            )
        ]

        # Check user's member status of connect group specifically
        user_status = get_user_connect_status(session["unix_name"], connect_group)

        domain_name = request.headers["Host"]

        if "usatlas" in domain_name:
            domain_name = "atlas.ci-connect.net"
        elif "uscms" in domain_name:
            domain_name = "cms.ci-connect.net"
        elif "uchicago" in domain_name:
            domain_name = "psdconnect.uchicago.edu"
        elif "snowmass21" in domain_name:
            domain_name = "snowmass21.ci-connect.net"

        with open(
            brand_dir
            + "/"
            + domain_name
            + "/form_descriptions/group_unix_name_description.md",
            "r",
        ) as file:
            group_unix_name_description = file.read()
        return render_template(
            "groups.html",
            groups=groups,
            user_status=user_status,
            group_unix_name_description=group_unix_name_description,
        )


@app.route("/groups/<group_name>", methods=["GET", "POST"])
@authenticated
def view_group(group_name):
    """Detailed view of specific groups"""
    # <LB> Appears unused.
    # query = {"token": ciconnect_api_token, "globus_id": session["primary_identity"]}

    user = get_user_info(session)
    unix_name = user["metadata"]["unix_name"]

    if request.method == "GET":
        # Get group information
        group = get_group_info(group_name, session)
        # print(group)
        group_creation_date = group["creation_date"].split(" ")[0]
        # Get User's Group Status
        user_status = get_user_group_status(unix_name, group_name, session)
        # Query to return user's enclosing group membership status
        enclosing_status = get_enclosing_group_status(group_name, unix_name)
        # Query to check user's connect group membership status
        connect_group = session["url_host"]["unix_name"]
        # print(connect_group)
        connect_status = get_user_connect_status(unix_name, connect_group)

        return render_template(
            "group_profile_overview.html",
            group=group,
            group_name=group_name,
            user_status=user_status,
            enclosing_status=enclosing_status,
            connect_status=connect_status,
            group_creation_date=group_creation_date,
        )
    elif request.method == "POST":
        """
        Request group membership by setting user status to pending
        """
        status = "pending"
        update_user_group_status(group_name, unix_name, status, session)
        # print("UPDATED MEMBERSHIP: {}".format(user_status))
        return redirect(url_for("view_group", group_name=group_name))


@app.route("/groups-xhr/<group_name>", methods=["GET"])
@authenticated
def view_group_ajax(group_name):
    group, user_status = view_group_ajax_request(group_name)
    return jsonify(group, user_status)


def view_group_ajax_request(group_name):
    # Get user info
    user = get_user_info(session)
    unix_name = user["metadata"]["unix_name"]
    # Get group info
    group = get_group_info(group_name, session)
    # Get User's Group Status
    user_status = get_user_group_status(unix_name, group_name, session)
    return group, user_status


@app.route("/groups/<group_name>/members", methods=["GET", "POST"])
@authenticated
def view_group_members(group_name):
    """Detailed view of group's members"""
    if request.method == "GET":
        # Get group information
        group = get_group_info(group_name, session)
        # Get User's Group Status
        unix_name = session["unix_name"]
        user_status = get_user_group_status(unix_name, group_name, session)
        # Query to return user's enclosing group's membership status
        enclosing_status = get_enclosing_group_status(group_name, unix_name)
        # Query to check user's connect status
        connect_group = session["url_host"]["unix_name"]
        connect_status = get_user_connect_status(unix_name, connect_group)

        return render_template(
            "group_profile_members.html",
            group_name=group_name,
            user_status=user_status,
            group=group,
            connect_status=connect_status,
            enclosing_status=enclosing_status,
        )


@app.route("/groups-xhr/<group_name>/members", methods=["GET"])
@authenticated
def view_group_members_ajax(group_name):
    user_dict, users_statuses = view_group_members_ajax_request(group_name)
    return jsonify(user_dict, users_statuses)


def view_group_members_ajax_request(group_name):
    """Detailed view of group's members"""
    query = {"token": ciconnect_api_token}
    if request.method == "GET":
        group_members = get_group_members(group_name, session)
        multiplexJson = {}
        users_statuses = {}
        # Get detailed user information from list of users
        for user in group_members:
            unix_name = user["user_name"]
            user_state = user["state"]
            if user_state != "nonmember" and unix_name != "root":
                user_query = "/v1alpha1/users/" + unix_name + "?token=" + query["token"]
                multiplexJson[user_query] = {"method": "GET"}
                users_statuses[unix_name] = user_state

        # POST request for multiplex return
        multiplex = get_multiplex(multiplexJson)
        user_dict = {}
        group_user_dict = {}

        for user in multiplex:
            user_name = user.split("/")[3].split("?")[0]
            user_dict[user_name] = json.loads(multiplex[user]["body"])

        for user, info in user_dict.items():
            for group_membership in info["metadata"]["group_memberships"]:
                if group_membership["name"] == group_name:
                    group_user_dict[user] = info

        return user_dict, users_statuses


@app.route("/groups-pending-members-count-xhr/<group_name>/members", methods=["GET"])
@authenticated
def group_pending_members_count_ajax(group_name):
    pending_user_count = group_pending_members_count_request(group_name)
    return jsonify(pending_user_count)


def group_pending_members_count_request(group_name):
    """Get a group's pending members count"""
    if request.method == "GET":
        group_members = get_group_members(group_name, session)
        pending_user_count = 0

        for user in group_members:
            if user["state"] == "pending":
                pending_user_count += 1

        return pending_user_count


@app.route("/groups/<group_name>/members-requests", methods=["GET", "POST"])
@authenticated
def view_group_members_requests(group_name):
    """Detailed view of group's pending members"""
    query = {"token": ciconnect_api_token}
    if request.method == "GET":
        # Get group information and group members
        group = get_group_info(group_name, session)
        group_members = get_group_members(group_name, session)

        # Set up multiplex while also tracking user status
        multiplexJson = {}
        users_statuses = {}
        for user in group_members:
            unix_name = user["user_name"]
            if user["state"] == "pending":
                user_state = user["state"]
                user_query = "/v1alpha1/users/" + unix_name + "?token=" + query["token"]
                multiplexJson[user_query] = {"method": "GET"}
                users_statuses[unix_name] = user_state

        # POST request for multiplex return
        multiplex = get_multiplex(multiplexJson)

        # Clean up multiplex return queries in user_dict
        user_dict = {}
        for user in multiplex:
            user_name = user.split("/")[3].split("?")[0]
            user_dict[user_name] = json.loads(multiplex[user]["body"])

        # Get User's Group Status
        unix_name = session["unix_name"]
        user_status = get_user_group_status(unix_name, group_name, session)

        # Query user's enclosing group status
        enclosing_status = get_enclosing_group_status(group_name, unix_name)

        # Query user's status in root connect group
        connect_group = session["url_host"]["unix_name"]
        connect_status = get_user_connect_status(unix_name, connect_group)

        return render_template(
            "group_profile_members_requests.html",
            group_members=user_dict,
            group_name=group_name,
            user_status=user_status,
            users_statuses=users_statuses,
            connect_status=connect_status,
            enclosing_status=enclosing_status,
            group=group,
        )


@app.route("/groups/<group_name>/add_members", methods=["GET", "POST"])
@authenticated
def view_group_add_members(group_name):
    """Detailed view of group's non-members"""
    query = {"token": ciconnect_api_token}
    if request.method == "GET":
        # Get group information
        group = get_group_info(group_name, session)

        # Get User's Group Status
        unix_name = session["unix_name"]
        user_status = get_user_group_status(unix_name, group_name, session)

        # Query user's enclosing group status
        enclosing_status = get_enclosing_group_status(group_name, unix_name)

        # Query user's status in root connect group
        connect_group = session["url_host"]["unix_name"]
        connect_status = get_user_connect_status(unix_name, connect_group)

        user_super = requests.get(
            ciconnect_api_endpoint + "/v1alpha1/users/" + session["unix_name"],
            params=query,
        )
        try:
            user_super = user_super.json()["metadata"]["superuser"]
        except:
            user_super = False

        return render_template(
            "group_profile_add_members.html",
            group_name=group_name,
            user_status=user_status,
            enclosing_status=enclosing_status,
            user_super=user_super,
            group=group,
            connect_status=connect_status,
        )


@app.route("/groups-xhr/<group_name>/add_members", methods=["GET", "POST"])
@authenticated
def view_group_add_members_xhr(group_name):
    """Detailed view of group's 'add members' page"""
    non_members = view_group_add_members_request(group_name)
    return jsonify(non_members)


def view_group_add_members_request(group_name):
    """Detailed view of group's non-members"""
    query = {"token": ciconnect_api_token}
    if request.method == "GET":
        # Get root base group users
        # If enclosing group is root
        # just display group_name connect group users
        # rather than all users in root i.e. from other connects
        group_name_list = group_name.split(".")
        if len(group_name_list) > 1:
            enclosing_group_name = ".".join(group_name_list[:-1])
        else:
            enclosing_group_name = group_name
        # Get all active members of enclosing group
        if enclosing_group_name:
            enclosing_group = get_group_members(enclosing_group_name, session)
            enclosing_group_members_names = [
                member["user_name"]
                for member in enclosing_group
                if member["state"] != "pending"
            ]
        else:
            enclosing_group_members_names = []
        # Get all members of current group
        group_members = get_group_members(group_name, session)
        memberships_names = [member["user_name"] for member in group_members]
        # Set the difference to filter all non-members of current group
        non_members = list(set(enclosing_group_members_names) - set(memberships_names))

        # Set up multiplex to query detailed info about all non-members
        multiplexJson = {}
        for user in non_members:
            unix_name = user
            user_query = "/v1alpha1/users/" + unix_name + "?token=" + query["token"]
            multiplexJson[user_query] = {"method": "GET"}

        # POST request for multiplex return and set up user_dict with user info
        multiplex = get_multiplex(multiplexJson)
        user_dict = {}
        for user in multiplex:
            user_name = user.split("/")[3].split("?")[0]
            user_dict[user_name] = json.loads(multiplex[user]["body"])

        return user_dict


@app.route("/groups/<group_name>/subgroups", methods=["GET", "POST"])
@authenticated
def view_group_subgroups(group_name):
    """Detailed view of group's subgroups"""
    if request.method == "GET":
        # Get group information
        group = get_group_info(group_name, session)
        # Get User's Group Status
        unix_name = session["unix_name"]
        user_status = get_user_group_status(unix_name, group_name, session)

        # Query to return user's enclosing group membership status
        enclosing_status = get_enclosing_group_status(group_name, unix_name)

        # Query to check if user's status in root brand group, i.e. CMS, SPT, OSG
        connect_group = session["url_host"]["unix_name"]
        connect_status = get_user_connect_status(unix_name, connect_group)

        domain_name = request.headers["Host"]

        if "usatlas" in domain_name:
            domain_name = "atlas.ci-connect.net"
        elif "uscms" in domain_name:
            domain_name = "cms.ci-connect.net"
        elif "uchicago" in domain_name:
            domain_name = "psdconnect.uchicago.edu"
        elif "snowmass21" in domain_name:
            domain_name = "snowmass21.ci-connect.net"

        with open(
            brand_dir
            + "/"
            + domain_name
            + "/form_descriptions/group_unix_name_description.md",
            "r",
        ) as file:
            group_unix_name_description = file.read()

        return render_template(
            "group_profile_subgroups.html",
            group_name=group_name,
            user_status=user_status,
            group=group,
            connect_status=connect_status,
            enclosing_status=enclosing_status,
            group_unix_name_description=group_unix_name_description,
        )


@app.route("/groups-xhr/<group_name>/subgroups", methods=["GET", "POST"])
@authenticated
def view_group_subgroups_xhr(group_name):
    """Detailed view of group's subgroups"""
    subgroups = view_group_subgroups_request(group_name)
    return jsonify(subgroups)


def view_group_subgroups_request(group_name):
    if request.method == "GET":
        # Get group's subgroups information
        group_index = len(group_name.split("."))
        subgroups = get_subgroups(group_name, session)

        # Split subgroup name by . to see how nested the group is
        # return subgroups that are group_index + 1 to ensure direct subgroup
        subgroups = [
            subgroup
            for subgroup in subgroups
            if (
                len(subgroup["name"].split(".")) == (group_index + 1)
                and not subgroup["pending"]
            )
        ]
        # Strip the root from display
        for subgroup in subgroups:
            clean_unix_name = ".".join(subgroup["name"].split(".")[1:])
            subgroup["clean_unix_name"] = clean_unix_name

        return subgroups


@app.route("/groups/<group_name>/subgroups-requests", methods=["GET", "POST"])
@authenticated
def view_group_subgroups_requests(group_name):
    """List view of group's subgroups requests"""
    query = {"token": ciconnect_api_token}
    if request.method == "GET":
        # Get group information
        group = get_group_info(group_name, session)

        # Get User's Group Status
        unix_name = session["unix_name"]
        user_status = get_user_group_status(unix_name, group_name, session)

        subgroup_requests = requests.get(
            ciconnect_api_endpoint
            + "/v1alpha1/groups/"
            + group_name
            + "/subgroup_requests",
            params=query,
        )
        subgroup_requests = subgroup_requests.json()["groups"]

        # Query to return user's enclosing membership status
        enclosing_status = get_enclosing_group_status(group_name, unix_name)

        # Query to check if user's status in root connect group
        connect_group = session["url_host"]["unix_name"]
        connect_status = get_user_connect_status(unix_name, connect_group)

        return render_template(
            "group_profile_subgroups_requests.html",
            subgroup_requests=subgroup_requests,
            group_name=group_name,
            user_status=user_status,
            group=group,
            connect_status=connect_status,
            enclosing_status=enclosing_status,
        )


@app.route("/groups-xhr/<group_name>/subgroups-requests", methods=["GET", "POST"])
@authenticated
def view_group_subgroups_ajax(group_name):
    subgroup_requests = view_group_subgroups_ajax_requests(group_name)
    subgroup_requests_count = len(subgroup_requests)
    return jsonify(subgroup_requests, subgroup_requests_count)


def view_group_subgroups_ajax_requests(group_name):
    """List view of group's subgroups requests"""
    query = {"token": ciconnect_api_token}
    if request.method == "GET":

        subgroup_requests = requests.get(
            ciconnect_api_endpoint
            + "/v1alpha1/groups/"
            + group_name
            + "/subgroup_requests",
            params=query,
        )
        subgroup_requests = subgroup_requests.json()["groups"]

        return subgroup_requests


@app.route("/groups/<group_name>/email", methods=["GET", "POST"])
@authenticated
def view_group_email(group_name):
    """View for email form to members"""
    if request.method == "GET":
        # Get group information
        group = get_group_info(group_name, session)
        # Get User's Group Status
        unix_name = session["unix_name"]
        user_status = get_user_group_status(unix_name, group_name, session)
        # Query to return user's enclosing group's membership status
        enclosing_status = get_enclosing_group_status(group_name, unix_name)
        # Query to check user's connect status
        connect_group = session["url_host"]["unix_name"]
        connect_status = get_user_connect_status(unix_name, connect_group)

        return render_template(
            "group_profile_email.html",
            group_name=group_name,
            user_status=user_status,
            group=group,
            connect_status=connect_status,
            enclosing_status=enclosing_status,
        )
    elif request.method == "POST":
        subject = request.form["subject"]
        body = request.form["description"]
        try:
            request.form["html-enabled"]
            body_or_html = "html"
        except:
            body_or_html = "text"

        # mailgun setup here
        domain_name = domain_name_edgecase()
        support_emails = {
            "cms.ci-connect.net": "cms-connect-support@cern.ch",
            "duke.ci-connect.net": "scsc@duke.edu",
            "spt.ci-connect.net": "jlstephen@uchicago.edu",
            "atlas.ci-connect.net": "atlas-connect-l@lists.bnl.gov",
            "psdconnect.uchicago.edu": "support@ci-connect.uchicago.edu",
            "www.ci-connect.net": "support@ci-connect.net",
            "localhost:5000": "jeremyvan614@gmail.com",
        }

        try:
            support_email = support_emails[domain_name]
        except:
            support_email = "support@ci-connect.net"

        user_dict, users_statuses = get_group_members_emails(group_name)
        user_emails = [user_dict[user]["metadata"]["email"] for user in user_dict]
        # print(user_emails)
        r = requests.post(
            "https://api.mailgun.net/v3/api.ci-connect.net/messages",
            auth=("api", mailgun_api_token),
            data={
                "from": "<" + support_email + ">",
                "to": [support_email],
                "bcc": user_emails,
                "subject": subject,
                body_or_html: body,
            },
        )
        if r.status_code == requests.codes.ok:
            flash("Your message has been sent to the members of this group", "success")
            return redirect(url_for("view_group_email", group_name=group_name))
        else:
            flash("Unable to send message: {}".format(r.json()), "warning")
            return redirect(url_for("view_group_email", group_name=group_name))
