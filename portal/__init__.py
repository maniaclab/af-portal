from flask import Flask
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta

# from flask import Markup
from flask_misaka import Misaka
import logging.handlers
import sys

__author__ = "MANIAC Lab <gardnergroup@lists.uchicago.edu>"

app = Flask(__name__)
# Enable CSRF protection globally for Flask app
csrf = CSRFProtect(app)
csrf.init_app(app)

if len(sys.argv) > 1:
    try:
        # Try to read config location from .ini file
        config_file = sys.argv[1]
        app.config.from_pyfile(config_file)
    except:
        print("Could not read config location from {}".format(sys.argv[1]))
else:
    print("Reading config file from local directory")
    app.config.from_pyfile("portal.conf")

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
