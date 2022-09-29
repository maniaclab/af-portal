from flask import  session, request, redirect, render_template, url_for
from functools import wraps
from portal import connect

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
        if not unix_name:
            return redirect(url_for('create_profile'))
        profile = connect.get_user_profile(unix_name)
        if not session.get('unix_id'):
            session['unix_id'] = profile['unix_id']
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
        if unix_name:
            profile = connect.get_user_profile(unix_name)
            role = profile['role'] if profile else 'nonmember'
            if role == 'admin':
                return fn(*args, **kwargs)
        return render_template('404.html')
    return decorated_function