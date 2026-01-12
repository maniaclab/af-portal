from flask import Flask
from flask_wtf.csrf import CSRFProtect
from jinja2_markdown import MarkdownExtension

app = Flask(__name__)
app.config.from_pyfile("secrets/portal.conf")
app.jinja_env.add_extension(MarkdownExtension)
csrf = CSRFProtect(app)
