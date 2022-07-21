from flask import redirect, request, session, url_for, render_template
from functools import wraps

def authenticated(fn):
    """Mark a route as requiring authentication."""
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if not session.get("is_authenticated"):
            return redirect(url_for("login", next=request.url))

        if request.path == "/logout":
            return fn(*args, **kwargs)

        if (not session.get("name") or not session.get("email") or not session.get("institution")) and request.path != "/profile":
            return redirect(url_for("create_profile", next=request.url))

        if not session.get("unix_name") and request.path != "/profile/new":
            return redirect(url_for("create_profile", next=request.url))

        return fn(*args, **kwargs)
    return decorated_function

def site_member(fn):
    """ Mark a route as requiring site membership """
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if not session.get("is_authenticated"):
            return redirect(url_for("login", next=request.url))

        if request.path == "/logout":
            return fn(*args, **kwargs)

        if (not session.get("name") or not session.get("email") or not session.get("institution")) and request.path != "/profile":
            return redirect(url_for("create_profile", next=request.url))

        if not session.get("unix_name") and request.path != "/profile/new":
            return redirect(url_for("create_profile", next=request.url))

        if not session.get("site_member"):
            return render_template("404.html")

        return fn(*args, **kwargs)
    return decorated_function

def site_admin(fn):
    """ Mark a route as requiring site admin privilege """
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if not session.get("is_authenticated"):
            return redirect(url_for("login", next=request.url))

        if request.path == "/logout":
            return fn(*args, **kwargs)

        if (not session.get("name") or not session.get("email") or not session.get("institution")) and request.path != "/profile":
            return redirect(url_for("create_profile", next=request.url))

        if not session.get("unix_name") and request.path != "/profile/new":
            return redirect(url_for("create_profile", next=request.url))

        if not session.get("admin") or session.get('admin') != 'admin':
            return render_template("404.html")

        return fn(*args, **kwargs)
    return decorated_function