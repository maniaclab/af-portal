from flask import session, request, render_template, jsonify, redirect, url_for, flash
import requests
from portal import app
from portal.decorators import authenticated
from portal.slate_api import get_app_config, get_app_readme, list_users_instances_request, get_instance_details, get_instance_logs, delete_instance
from portal.connect_api import get_user_profile
import os
# import yaml, json
from base64 import b64encode