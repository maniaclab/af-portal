from flask import session
import requests
import os
from base64 import b64encode
from portal import app

slate_api_token = app.config['SLATE_API_TOKEN']
slate_api_endpoint = app.config['SLATE_API_ENDPOINT']
query = {'token': slate_api_token}

# Install Jupyter

def generateToken():
    token_bytes = os.urandom(32)
    b64_encoded = b64encode(token_bytes).decode()
    return b64_encoded