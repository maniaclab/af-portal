'''
This module supports the JupyterLab service

Functionality:
=============== 

1. The load_kube_config method loads a kubeconfig file (either the file specified or ~/.kube/config)
2. The start_notebook_maintenance method starts a thread for removing expired notebooks
3. The deploy_notebook method lets a user deploy a notebook onto our Kubernetes cluster
4. The get_notebook function lets a user get data for a single notebook
5. The get_notebooks function lets a user get data for all of a user's notebooks
6. The remove_notebook function lets a user remove a notebook
7. The list_notebooks function returns a list of the names of all currently running notebooks
8. The get_gpu_availability function lets a user know which GPU products are available for use.
9. The get_notebook_status function gets the status of a notebook (ready, starting, pending, removing)

Dependencies:
=============== 

1. A portal.conf configuration file (af-portal/portal/secrets/portal.conf)
2. A kubeconfig file (either a file specified in portal.conf, or a file at the default location, ~/.kube/config)

Example usage:
=============== 

Example #1:

cd <path>/<to>/af-portal
python 
>>> from portal import jupyterlab
>>> from pprint import pprint
>>> jupyterlab.load_kube_config()
>>> notebook = jupyterlab.get_notebook('example-notebook-1')
>>> pprint(notebook)

Example #2:

cd <path>/<to>/af-portal
python 
>>> from portal import jupyterlab
>>> from pprint import pprint
>>> jupyterlab.load_kube_config()
>>> notebooks = jupyterlab.get_notebooks('my-username')
>>> pprint(notebooks)

Example #3:

cd <path>/<to>/af-portal
python 
>>> from portal import jupyterlab
>>> from pprint import pprint
>>> jupyterlab.load_kube_config()
>>> settings = {
'notebook_name': 'MyNotebook',
'notebook_id': 'mynotebook',
'image': 'ml-platform:latest',
'owner': 'myusername',
'owner_uid': 2468,
'globus_id': 'alphanumeric string with hyphens',
'cpu_request': 1,
'cpu_limit': 2,
'memory_request': '1Gi',
'memory_limit': '2Gi',
'gpu_request': 1,
'gpu_limit': 1,
'gpu_memory': 4864,
'hours_remaining': 168
}
>>> jupyterlab.deploy_notebook(**settings)
>>> notebook = jupyterlab.get_notebook('mynotebook', url=True)
>>> pprint(notebook)

Example #4:

cd <path>/<to>/af-portal
python 
>>> from portal import jupyterlab
>>> help(jupyterlab)
>>> help(jupyterlab.deploy_notebook)
>>> help(jupyterlab.get_notebook)
>>> help(jupyterlab.get_notebooks)

Example #5:

cd <path>/<to>/af-portal
python
>>> from portal import jupyterlab
>>> from pprint import pprint
>>> jupyterlab.load_kube_config()
>>> avail = jupyterlab.get_gpu_availability()
>>> pprint(avail)
>>> gpu1 = jupyterlab.get_gpu_availability(product='NVIDIA-A100-SXM4-40GB')
>>> pprint(gpu1)
>>> gpu2 = jupyterlab.get_gpu_availability(memory=4864)
>>> pprint(gpu2)
'''
import yaml
import time
import datetime
import threading
import os
import re
import urllib
from base64 import b64encode
from datetime import timezone
from jinja2 import Environment, FileSystemLoader
from kubernetes import client, config
from portal import app, logger, utils

namespace = app.config['NAMESPACE']

def load_kube_config():
    config_file = app.config.get('KUBECONFIG')
    if config_file:
        config.load_kube_config(config_file=config_file)
        logger.info('Loaded kubeconfig from file %s' %config_file)
    else:
        config.load_kube_config()
        logger.info('Loaded default kubeconfig file')

def start_notebook_maintenance():
    def clean():
        while True:
            api = client.CoreV1Api()
            pods = api.list_namespaced_pod(namespace, label_selector='k8s-app=jupyterlab').items
            for pod in pods:
                notebook_name = pod.metadata.name
                exp_date = get_expiration_date(pod=pod)
                now = datetime.datetime.now(timezone.utc)
                if exp_date and exp_date < now:
                    logger.info('Notebook %s has expired' %notebook_name)
                    remove_notebook(notebook_name)                        
            time.sleep(1800)
    threading.Thread(target=clean).start()
    logger.info('Started notebook maintenance')

def deploy_notebook(**settings):
    '''
    Deploys a Jupyter notebook on our Kubernetes cluster.

    Function parameters:
    (All parameters are required.)

    notebook_name: (string) The display name of the notebook
    notebook_id: (string) A unique name for the notebook
    image: (string) The Docker image that will be run in the pod's container
    owner: (string) The username of the notebook's owner 
    owner_uid: (integer) The numeric ID of the notebook's owner 
    globus_id: (string) The Globus ID of the notebook's owner
    cpu_request: (integer) The number of CPU cores to request from the k8s cluster
    cpu_limit: (integer) The max number of CPU cores that can be allocated to this pod
    memory_request: (string) The amount of memory to request from the k8s cluster (e.g. '1Gi')
    memory_limit: (string) The max amount of memory that can be allocated to this pod
    gpu_request: (integer) The number of GPU instances to request from the k8s cluster
    gpu_limit: (integer) The max number of GPU instances that can be allocated to this pod
    gpu_memory: (integer) Selects a GPU product based on its memory, in megabytes (e.g. 4864)
    hours_remaining: (integer) The duration of the notebook in hours
    '''
    settings['namespace'] = namespace
    settings['domain_name'] = app.config['DOMAIN_NAME']
    settings['token'] = b64encode(os.urandom(32)).decode()
    templates = Environment(loader=FileSystemLoader('portal/templates/jupyterlab'))
    api = client.CoreV1Api()
    # Create a pod for the notebook (the notebook runs as a container inside the pod)
    template = templates.get_template('pod.yaml')
    pod = yaml.safe_load(template.render(**settings))  
    api.create_namespaced_pod(namespace=namespace, body=pod)
    # Create a service for the pod
    template = templates.get_template('service.yaml')
    service = yaml.safe_load(template.render(**settings))
    api.create_namespaced_service(namespace=namespace, body=service)
    # Store the JupyterLab token in a secret
    template = templates.get_template('secret.yaml')
    secret = yaml.safe_load(template.render(**settings))
    api.create_namespaced_secret(namespace=namespace, body=secret)
    # Create an ingress for the service (gives the notebook its own domain name and public key certificate)
    api = client.NetworkingV1Api()
    template = templates.get_template('ingress.yaml')
    ingress = yaml.safe_load(template.render(**settings))
    api.create_namespaced_ingress(namespace=namespace, body=ingress)
    logger.info('Deployed notebook %s' %settings['notebook_name'])

def get_notebook(name=None, pod=None, **options):
    '''
    Looks up a notebook by name or by pod. Returns a dict.

    Function parameters:
    (Either a name or a pod is required to look up a notebook.)

    name: (string) The name of the notebook
    pod: (object) The pod object returned by the kubernetes client
    log: (boolean) When log is True, the pod log is included in the dict that gets returned
    url: (boolean) When url is True, the notebook URL is included in the dict that gets returned
    '''
    api = client.CoreV1Api()
    if pod is None:
        pod = api.read_namespaced_pod(name=name.lower(), namespace=namespace)
    notebook = dict()
    notebook['id'] = pod.metadata.name
    notebook['name'] = pod.metadata.labels.get('notebook-name') or pod.metadata.labels.get('display-name')
    notebook['namespace'] = namespace
    notebook['owner'] = pod.metadata.labels.get('owner')
    notebook['image'] = pod.spec.containers[0].image
    notebook['node'] = pod.spec.node_name
    notebook['node_selector'] = pod.spec.node_selector
    notebook['status'] = get_notebook_status(pod=pod)
    notebook['pod_status'] = pod.status.phase
    notebook['creation_date'] = pod.metadata.creation_timestamp.isoformat()
    notebook['requests'] = pod.spec.containers[0].resources.requests
    notebook['limits'] = pod.spec.containers[0].resources.limits
    notebook['conditions'] = [{'type': c.type, 'status': c.status, 'timestamp': c.last_transition_time.isoformat()} for c in pod.status.conditions]
    notebook['conditions'].sort(key=lambda cond : dict(PodScheduled=0, Initialized=1, ContainersReady=2, Ready=3).get(cond['type']))
    events = api.list_namespaced_event(namespace=namespace, field_selector='involvedObject.uid=%s' %pod.metadata.uid).items
    notebook['events'] = [{'message': event.message, 'timestamp': event.last_timestamp.isoformat()} for event in events]
    if pod.spec.node_name:
        node = api.read_node(pod.spec.node_name)
        if node.metadata.labels.get('gpu') == 'true':
            notebook['gpu'] = {'product': node.metadata.labels['nvidia.com/gpu.product'], 'memory':  node.metadata.labels['nvidia.com/gpu.memory'] + 'Mi'}
    expiration_date = get_expiration_date(pod=pod)
    time_remaining = expiration_date - datetime.datetime.now(timezone.utc)
    notebook['expiration_date'] = expiration_date.isoformat()
    notebook['hours_remaining'] = int(time_remaining.total_seconds() / 3600)
    # Optional fields
    if options.get('log') is True:
        notebook['log'] = api.read_namespaced_pod_log(name=name.lower(), namespace=namespace)
    if options.get('url') is True and pod.metadata.deletion_timestamp is None:
        token = api.read_namespaced_secret(pod.metadata.name, namespace).data['token']
        notebook['url'] = 'https://%s.%s?%s' %(pod.metadata.name, app.config['DOMAIN_NAME'], urllib.parse.urlencode({'token': token}))
    return notebook

def get_notebooks(owner=None):
    '''
    Retrieves a user's notebooks, or the notebooks for all users. Returns an array of dicts.

    Function parameters:
    (The owner parameter is optional.)

    owner: (string) The username of the owner. When owner is None, the function returns all notebooks for all users.
    '''
    notebooks = []
    api = client.CoreV1Api()
    selector = 'k8s-app=jupyterlab' if owner is None else 'k8s-app=jupyterlab,owner=%s' %owner
    pods = api.list_namespaced_pod(namespace, label_selector=selector).items 
    for pod in pods:
        try:
            notebook = get_notebook(pod=pod, url=True)
            notebooks.append(notebook)
        except Exception as err:
            logger.error('Error adding notebook %s to array.' %pod.metadata.name)
            logger.error(str(err))
    return notebooks

def list_notebooks():
    ''' Returns a list of the names of all notebooks in the namespace. '''
    notebooks = []
    api = client.CoreV1Api()
    pods = api.list_namespaced_pod(namespace=namespace, label_selector='k8s-app=jupyterlab').items
    for pod in pods:
        notebooks.append(pod.metadata.name)
    return notebooks

def remove_notebook(name):
    ''' Removes a notebook from the namespace, and all Kubernetes objects associated with the notebook. '''
    id = name.lower()
    api = client.CoreV1Api()
    api.delete_namespaced_pod(id, namespace)
    api.delete_namespaced_service(id, namespace)
    api.delete_namespaced_secret(id, namespace)
    api = client.NetworkingV1Api()
    api.delete_namespaced_ingress(id, namespace)
    logger.info('Removed notebook %s from namespace %s' %(id, namespace))

def notebook_name_available(name):
    ''' Returns a boolean indicating whether a notebook name is available for use. '''
    id = name.lower()
    api = client.CoreV1Api()
    pods = api.list_namespaced_pod(namespace, label_selector='notebook-id={0}'.format(id))
    return len(pods.items) == 0

def generate_notebook_name(owner):
    ''' Returns a default notebook name that is available for use, e.g. testuser-notebook-3. '''
    for i in range(1, 20):
        notebook_name = f'{owner}-notebook-{i}'
        if notebook_name_available(notebook_name):
            return notebook_name
    return None

def supported_images():
    ''' Returns a tuple of Docker images that are supported by the JupyterLab service. '''
    return ('hub.opensciencegrid.org/usatlas/ml-platform:latest', 'hub.opensciencegrid.org/usatlas/ml-platform:conda', 
            'hub.opensciencegrid.org/usatlas/ml-platform:julia', 'hub.opensciencegrid.org/usatlas/ml-platform:lava',
            'hub.opensciencegrid.org/usatlas/ml-platform:centos7-experimental')

def get_gpu_availability(product=None, memory=None):
    ''' 
    Looks up a GPU product by its product name or memory cache size, and gets its availability.
    When this function is called without arguments, it gets the availability of every GPU product.
    Returns a list of dicts.
    
    Function parameters:
    (Both parameters are optional.)

    product: (string) The GPU product name
    memory: (int) The GPU memory cache size in megabytes (e.g. 40536)

    Algorithm for getting GPU availability:
    1. Create a hash map of GPUs grouped by their product name.
    2. Get a set of Kubernetes nodes that have GPU support.
        a. If a product name or cache size is specified, get the set of nodes that supports the product.
        b. If no product name or cache size is specified, get the set of all nodes that are labeled gpu=true.
    3. Iterate over the set of Kubernetes nodes.
        a. Get the GPU that is used by the node.
        b. Update the hash map.
            i. If the GPU is not in our hash map, add its name, cache size, and count to the hash map.
            ii. If the GPU is in our hash map, increase its count.
        b. Get the set of pods running on this node.
        c. Iterate over the set of pods
            i. Add up all the pod requests for this GPU
        d. To calculate availability, subtract the total number of requests for this GPU from the total number of instances
           <Number of available GPU instances> = <Number of GPU instances> - <Number of GPU requests>
    4. Get the hash map values as a list. Sort the list. Each entry in the list gives the availability of a unique GPU product.
       Return the sorted list of dicts. 
    '''
    gpus = dict()
    api = client.CoreV1Api()
    if product:
        nodes = api.list_node(label_selector='gpu=true,nvidia.com/gpu.product=%s' %product)
    elif memory:
        nodes = api.list_node(label_selector='gpu=true,nvidia.com/gpu.memory=%s' %memory)
    else: 
        nodes = api.list_node(label_selector='gpu=true') 
    for node in nodes.items:
        product = node.metadata.labels['nvidia.com/gpu.product']
        memory = int(node.metadata.labels['nvidia.com/gpu.memory'])
        count = int(node.metadata.labels['nvidia.com/gpu.count'])
        if product not in gpus:
            gpus[product] = dict(product=product, memory=memory, count=count)
        else:
            gpus[product]['count'] += count
        gpu = gpus[product]
        gpu['total_requests'] = 0
        pods = api.list_pod_for_all_namespaces(field_selector='spec.nodeName=%s' %node.metadata.name).items
        for pod in pods:
            requests = pod.spec.containers[0].resources.requests
            if requests:
                gpu['total_requests'] += int(requests.get('nvidia.com/gpu', 0))
        gpu['available'] = max(gpu['count'] - gpu['total_requests'], 0)
    return sorted(gpus.values(), key=lambda gpu : gpu['memory'])

def get_notebook_status(name=None, pod=None):
    ''' Returns the status of a notebook as a string. '''
    if pod is None:
        pod = get_pod(name)
    if pod.metadata.deletion_timestamp:
        return 'Removing notebook...'
    ready = next(filter(lambda c : c.type == 'Ready' and c.status == 'True', pod.status.conditions), None)
    if ready:
        api = client.CoreV1Api()
        log = api.read_namespaced_pod_log(pod.metadata.name, namespace=namespace)
        if re.search('Jupyter Notebook.*is running at', log) or re.search('Jupyter Server.*is running at', log):
            return 'Ready'
        return 'Starting notebook...'   
    return 'Pending'

def get_expiration_date(name=None, pod=None):
    ''' Looks up a notebook by its name or pod, and returns its expiration date as a datetime object '''
    if pod is None:
        pod = get_pod(name)
    pattern = re.compile(r'ttl-\d+')
    if pattern.match(pod.metadata.labels['time2delete']):
        hours = int(pod.metadata.labels['time2delete'].split('-')[1])
        return pod.metadata.creation_timestamp + datetime.timedelta(hours=hours)
    return None

def get_pod(name):
    api = client.CoreV1Api()
    return api.read_namespaced_pod(name=name, namespace=namespace)