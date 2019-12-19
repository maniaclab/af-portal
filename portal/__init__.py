from flask import Flask
import json

# from flask import Markup
from flask_misaka import markdown
from flask_misaka import Misaka
import logging.handlers
import logging
import sys

__author__ = 'Jeremy Van <jeremyvan@uchicago.edu>'

app = Flask(__name__)

if len(sys.argv) > 1:
    try:
        # Try to read config location from .ini file
        config_file = sys.argv[1]
        app.config.from_pyfile(config_file)
    except:
        print("Could not read config location from {}".format(sys.argv[1]))
else:
    print("Reading config file from local directory")
    app.config.from_pyfile('portal.conf')

app.url_map.strict_slashes = False

# set up Markdown Rendering
md = Misaka()
md.__init__(app, tables=True, autolink=True, fenced_code=True, smartypants=True, quote=True, math=True, math_explicit=True)

import portal.views
