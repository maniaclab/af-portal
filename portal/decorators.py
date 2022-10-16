''' 
Decorators that are used by the application. 

The Decorator pattern
======================

The @ operator in Python is a binary operator that takes two functions d and f as operands.

The @(d, f) operation does the following:

    @(d, f):
        f = d(f)

This operation updates the module's symbol table, and maps the symbol "f" to the address in memory
where the decorated function d(f) is located.

The decorator pattern allows us to replace a function, and give it an additional feature.

Examples:
======================

Example #1:

def timer(fn):
    def inner(*args, **kwargs):
        start = time.time()
        return_value = fn(*args, **kwargs)
        end = time.time()
        print('Fuction %s took %f seconds' %(fn.__name__, end-start))
        return return_value
    return inner

@timer
def add(a, b)
    return a + b

In the example above, the @ operator performs the following:

    add = timer(add)

The module's symbol table gets updated, and the symbol "add" gets mapped to a new address in memory.

The new address in memory stores the newly decorated function, timer(add).

This is possible because timer is a function that takes a function as an argument, and returns a function.

Thus we see how we can easily add functionality to any function by adding the code @timer directly above the function definition.

Example #2:

# module app
request_handlers = {}

def route(url):
    def inner(fn):
        request_handlers[url] = fn
        return fn
    return inner

# module views
@app.route("/")
def home():
    return "Hello world"

In the example above, we show how Flask maps URLs to request handlers.

When the line of code @app.route("/") is interpreted, the function call app.route("/") returns a decorator function.
Let's call this decorator d.

Thus @app.route("/") becomes @d.

@d
def home():
    return "Hello world"

The above code performs an operation.

@(d, home):
    home = d(home)

Since the decorator function d returns whatever function it is passed, the symbol table entry for "home" does not need to be updated.

But what the @(d, home) operation does accomplish is that it maps the "/" URL to the home function in the app.request_handlers dictionary.

We can actually do this without using the @ operator.

# module app
request_handlers = {}

# module views
def home():
    return "Hello world"

app.request_handlers["/"] = home

This is how the Django web framework maps URLs to request handlers, without using the @ operator.

Both the Flask web framework and the Django web framework have very helpful ways of organizing request handlers.

The Flask framework's @route decorator does more than map a URL to a request handler. 
It also gives the request handler access to the request and response objects, which are in the namespace of the decorator.
'''
from flask import session, request, redirect, render_template, url_for, flash
from functools import wraps
from portal import connect, jupyterlab, logger
from portal.errors import InvalidParameter, MissingParameter, InvalidFormError
import time
import string

def timer(fn):
    ''' Times a function, and logs how much time it takes. '''
    @wraps(fn)
    def inner(*args, **kwargs):
        start = time.time()
        return_value = fn(*args, **kwargs)
        end = time.time()
        logger.info('Function %s took %f seconds' %(fn.__name__, end-start))
        return return_value
    return inner

def permit_keys(*keys):
    ''' A function that returns a decorator. The decorator raises an Exception when a key is not permitted. '''
    def outer(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            for kw in kwargs:
                if kw not in keys:
                    raise InvalidParameter(kw)
            return fn(*args, **kwargs)
        return inner
    return outer

def require_keys(*keys):
    ''' A function that returns a decorator. The decorator raises an Exception when a required key is missing. '''
    def outer(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            for key in keys:
                if key not in kwargs:
                    raise MissingParameter(key)
            return fn(*args, **kwargs)
        return inner
    return outer

def login_required(fn):
    ''' Requires the session user to be logged in.'''
    @wraps(fn)
    def inner(*args, **kwargs):
        if not session.get('is_authenticated'):
            return redirect(url_for('login', next=request.url))
        return fn(*args, **kwargs)
    return inner

def members_only(fn):
    ''' Requires the session user to be a member. '''
    @wraps(fn)
    def inner(*args, **kwargs):
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
    return inner

def admins_only(fn):
    ''' Requires the session user to be an admin. '''
    @wraps(fn)
    def inner(*args, **kwargs):
        if not session.get('is_authenticated'):
            return redirect(url_for('login', next=request.url))
        unix_name = session.get('unix_name')
        if unix_name:
            profile = connect.get_user_profile(unix_name)
            role = profile['role'] if profile else 'nonmember'
            if role == 'admin':
                return fn(*args, **kwargs)
        return render_template('404.html')
    return inner

def validate_notebook(fn):
    ''' Validates the form for creating a new Jupyter notebook. '''
    @wraps(fn)
    def inner(*args, **kwargs):
        try:
            valid_chars = set(string.ascii_lowercase + string.ascii_uppercase + string.digits + '_' + '-' + '.')
            notebook_name = request.form['notebook-name']
            image = request.form['image']
            cpu_request = int(request.form['cpu'])
            memory_request = int(request.form['memory'])
            gpu_request = int(request.form['gpu'])
            gpu_memory_request = int(request.form['gpu-memory'])
            if ' ' in notebook_name:
                raise InvalidFormError('The notebook name cannot have any whitespace.')
            if len(notebook_name) > 30:
                raise InvalidFormError('The notebook name cannot exceed 30 characters.')
            if not set(notebook_name) <= valid_chars:
                raise InvalidFormError('Valid characters are [a-zA-Z0-9._-]')
            if not jupyterlab.notebook_name_available(notebook_name):
                raise InvalidFormError('The name %s is already taken.' %notebook_name) 
            if image not in jupyterlab.supported_images():
                raise InvalidFormError('Docker image %s is not supported.' %image)
            if cpu_request < 1 or cpu_request > 4:
                raise InvalidFormError('The request of %d CPUs is outside the bounds [1, 4].' %cpu_request)
            if memory_request < 0 or memory_request > 32:
                raise InvalidFormError('The request of %d GB is outside the bounds [1, 32].' %memory_request)
            if gpu_request < 0 or gpu_request > 7:
                raise InvalidFormError('The request of %d GPUs is outside the bounds [0, 7].' %gpu_request)
            gpus = jupyterlab.get_gpu_availability(memory=gpu_memory_request)
            if not gpus:
                raise InvalidFormError('The GPU product is not supported.')
            gpu_product = gpus[0]['product']
            gpu_available = gpus[0]['available']
            if gpu_available < gpu_request:
                if gpu_available == 0:
                    raise InvalidFormError('The %s is currently not available' %gpu_product)
                if gpu_available == 1:
                    raise InvalidFormError('The %s has only 1 instance available.' %gpu_product)
                if gpu_available > 1:
                    raise InvalidFormError('The %s has only %s instances available.' %(gpu_product, gpu_available))
            return fn(*args, **kwargs)
        except InvalidFormError as err:
            flash(str(err), 'warning')
            return redirect(url_for('configure_notebook'))
    return inner