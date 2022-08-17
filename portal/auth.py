from flask import  session, request, redirect, render_template, url_for
from functools import wraps
from portal import connect, logger

def login_required(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if not session.get("is_authenticated"):
            return redirect(url_for("login", next=request.url))
        return fn(*args, **kwargs)
    return decorated_function

def members_only(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if not session.get("is_authenticated"):
            return redirect(url_for("login", next=request.url))
        unix_name = session.get("unix_name")
        globus_id = session.get("globus_id")
        member_status = connect.get_member_status(unix_name, globus_id)
        if member_status in ("admin", "active"):
            return fn(*args, **kwargs)
        return render_template("request_membership.html", member_status=member_status)
    return decorated_function

def admins_only(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if not session.get("is_authenticated"):
            return redirect(url_for("login", next=request.url))
        unix_name = session.get("unix_name")
        globus_id = session.get("globus_id")
        member_status = connect.get_member_status(unix_name, globus_id)
        if member_status == "admin":
            return fn(*args, **kwargs)
        return redirect(url_for("home"))
    return decorated_function