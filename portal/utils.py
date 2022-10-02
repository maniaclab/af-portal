from functools import wraps
from portal import logger
import time

def timer(fn):
    '''
    A decorator that times a decorated function, and logs how much time it takes.
    This feature can be applied by adding @utils.timer directly above any function definition.

    Example (taken from jupyterlab.py):

    @utils.timer
    def get_gpu_info(product=None, memory=None):
        ...

    @utils.timer
    def get_notebooks(owner=None)
        ...

    gpus = jupyterlab.get_gpu_info()
    notebooks = jupyterlab.get_notebooks('testuser')
    '''
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        start = time.time()
        return_value = fn(*args, **kwargs)
        end = time.time()
        logger.info('Function %s took %f seconds' %(fn.__name__, end-start))
        return return_value
    return decorated_function