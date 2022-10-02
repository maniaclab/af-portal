# This module has decorator functions for server-side form validation.
# We do client-side form validation with HTML and JavaScript, and server-side form validation with Python.

from flask import request, redirect, render_template, url_for, flash
from functools import wraps
import string
from portal import jupyterlab

class InvalidFormError(Exception):
    pass

def valid_notebook(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
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
            gpus = jupyterlab.get_gpu_info(memory=gpu_memory_request)
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
    return decorated_function