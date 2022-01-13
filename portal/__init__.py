from flask import Flask
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta

# from flask import Markup
from flask_misaka import Misaka
import logging.handlers
import sys

from portal import log_api
logger = log_api.init_logger()

__author__ = "MANIAC Lab <gardnergroup@lists.uchicago.edu>"

app = Flask(__name__)
# Enable CSRF protection globally for Flask app
csrf = CSRFProtect(app)
csrf.init_app(app)

if len(sys.argv) > 1:
    try:
        # Try to read config location from .ini file
        logger.info("Reading config file from sys.argv[1]")
        config_file = sys.argv[1]
        app.config.from_pyfile(config_file)
        logger.info("Read config file from sys.argv[1]")
    except:
        logger.info("Could not read config location from {}".format(sys.argv[1]))
else:
    logger.info("Reading config file from local directory")
    app.config.from_pyfile("portal.conf")
    logger.info("Read config file from local directory")

from portal import k8s_api
kubeconfig = app.config.get("KUBECONFIG")
if kubeconfig:
    logger.info("kubeconfig file is " + kubeconfig)
else:
    logger.info("kubeconfig file is the default file")

logger.info("Loading kube config")
k8s_api.load_kube_config()
logger.info("Loaded kube config")

logger.info("Starting k8s notebook manager")
k8s_api.start_notebook_manager('atlas-af-test')
logger.info("Started k8s notebook manager")

app.url_map.strict_slashes = False
app.permanent_session_lifetime = timedelta(minutes=1440)
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
# set up Markdown Rendering
md = Misaka()
md.__init__(
    app,
    tables=True,
    autolink=True,
    fenced_code=True,
    smartypants=True,
    quote=True,
    math=True,
    math_explicit=True,
)

import portal.views
