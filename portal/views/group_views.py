# 201 - 940
from flask import (flash, redirect, render_template, request,
                   session, url_for, jsonify)
import requests
import json

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from portal import app
from portal.decorators import authenticated
from portal.utils import flash_message_parser
from portal.connect_api import (get_user_info, get_multiplex, get_user_connect_status,
                        get_subgroups,get_group_info, get_group_members,
                        get_user_group_status, get_enclosing_group_status,
                        update_user_group_status, delete_group_entry)
import sys

# Read configurable tokens and endpoints from config file, values must be set
ciconnect_api_token = app.config['CONNECT_API_TOKEN']
ciconnect_api_endpoint = app.config['CONNECT_API_ENDPOINT']
mailgun_api_token = app.config['MAILGUN_API_TOKEN']
# Read Brand Dir from config and insert path to read
brand_dir = app.config['MARKDOWN_DIR']
sys.path.insert(0, brand_dir)

@app.route('/groups', methods=['GET'])
def groups():
    """Connect groups"""
    if request.method == 'GET':
        connect_group = session['url_host']['unix_name']
        # Get group's subgroups information
        groups = get_subgroups(connect_group, session)
        # Filter subgroups directly one level nested under group
        group_index = len(connect_group.split('.'))
        groups = [group for group in groups if (
            len(group['name'].split('.')) == (group_index + 1) and not group['pending'])]

        # Check user's member status of connect group specifically
        user_status = get_user_connect_status(session['unix_name'], connect_group)

        domain_name = request.headers['Host']
        with open(brand_dir + '/' + domain_name + "/form_descriptions/group_unix_name_description.md", "r") as file:
            group_unix_name_description = file.read()
        print("REFACTORED")
        return render_template('groups.html', groups=groups,
                               user_status=user_status,
                               group_unix_name_description=group_unix_name_description)
