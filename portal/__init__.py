from flask import Flask
from flask_wtf.csrf import CSRFProtect
from jinja2_markdown import MarkdownExtension
import logging

app = Flask(__name__)
app.config.from_pyfile('secrets/portal.conf')
app.jinja_env.add_extension(MarkdownExtension)
csrf = CSRFProtect(app)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s;%(module)s;%(funcName)s;%(levelname)s;%(message)s')
logger.propagate = False
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)
fh = logging.FileHandler('portal.log')
fh.setLevel(logging.INFO)
fh.setFormatter(formatter)
logger.addHandler(fh)

import portal.views
