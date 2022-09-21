from flask import  session, request, redirect, render_template, url_for
from functools import wraps
from portal import connect, logger

def login_required(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if not session.get('is_authenticated'):
            return redirect(url_for('login', next=request.url))
        return fn(*args, **kwargs)
    return decorated_function

def members_only(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if not session.get('is_authenticated'):
            return redirect(url_for('login', next=request.url))
        unix_name = session.get('unix_name')
        profile = connect.get_user_profile(unix_name)
        role = profile['role']
        if role == 'admin' or role == 'active':
            return fn(*args, **kwargs)
        return render_template('request_membership.html', role=role)
    return decorated_function

def admins_only(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if not session.get('is_authenticated'):
            return redirect(url_for('login', next=request.url))
        unix_name = session.get('unix_name')
        profile = connect.get_user_profile(unix_name)
        role = profile['role']
        if role == 'admin':
            return fn(*args, **kwargs)
        return render_template('404.html')
    return decorated_function