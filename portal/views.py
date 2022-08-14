from portal import app
from flask import render_template

@app.route("/", methods=["GET"])
def home():
    return render_template("home.html")

@app.route("/about", methods=["GET"])
def about():
    return render_template("about.html")