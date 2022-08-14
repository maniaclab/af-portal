from flask import Flask
from jinja2_markdown import MarkdownExtension

app = Flask(__name__)
app.jinja_env.add_extension(MarkdownExtension)

import portal.views