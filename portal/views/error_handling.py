from flask import render_template, request
import traceback
import time
import sys
from werkzeug.exceptions import HTTPException
from portal import app


# Create a custom error handler for Exceptions
@app.errorhandler(Exception)
def exception_occurred(e):
    trace = traceback.format_tb(sys.exc_info()[2])
    app.logger.error(
        "{0} Traceback occurred:\n".format(time.ctime())
        + "{0}\nTraceback completed".format("n".join(trace))
    )
    trace = "<br>".join(trace)
    trace.replace("\n", "<br>")
    return render_template("error.html", exception=trace, debug=app.config["DEBUG"])


@app.route("/error", methods=["GET"])
def errorpage():
    if request.method == "GET":
        return render_template("error.html")


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html")


@app.errorhandler(Exception)
def handle_exception(e):
    # pass through HTTP errors
    if isinstance(e, HTTPException):
        return e
    # now you're handling non-HTTP exceptions only
    return render_template("500.html", e=e), 500
