# This module supports the JupyterLab service.
# The main interface is near the top, and below the main interface are helper functions.
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
from portal import app, logger

namespace = app.config['NAMESPACE']

@app.before_first_request
def load_kube_config():
    config_file = app.config.get('KUBECONFIG')
    if config_file:
        config.load_kube_config(config_file=config_file)
        logger.info('Loaded kubeconfig from file %s' %config_file)
    else:
        config.load_kube_config()
        logger.info('Loaded default kubeconfig file')

@app.before_first_request
def start_notebook_maintenance():
    def clean():
        while True:
            api = client.CoreV1Api()
            pods = api.list_namespaced_pod(namespace, label_selector='k8s-app=jupyterlab').items
            for pod in pods:
                notebook_name = pod.metadata.name
                exp_date = get_expiration_date(pod)
                now = datetime.datetime.now(timezone.utc)
                if exp_date and exp_date < now:
                    logger.info('Notebook %s has expired' %notebook_name)
                    remove_notebook(notebook_name)                        
            time.sleep(1800)
    threading.Thread(target=clean).start()
    logger.info('Started notebook maintenance')

# Function description: Deploys a Jupyter notebook on our Kubernetes cluster.
#
# Function parameters:
# (All parameters below are required.)
#
# notebook_name: (string) The display name of the notebook
# notebook_id: (string) A unique name for the notebook
# image: (string) The Docker image that will be run in the pod's container
# owner: (string) The username of the notebook's owner 
# owner_uid: (integer) The numeric ID of the notebook's owner 
# globus_id: (string) The Globus ID of the notebook's owner
# cpu_request: (integer) The number of CPU cores to request from the k8s cluster
# cpu_limit: (integer) The max number of CPU cores that can be allocated to this pod
# memory_request: (string) The amount of memory to request from the k8s cluster (e.g. '1Gi')
# memory_limit: (string) The max amount of memory that can be allocated to this pod
# gpu_request: (integer) The number of GPU instances to request from the k8s cluster
# gpu_limit: (integer) The max number of GPU instances that can be allocated to this pod
# gpu_memory: (integer) Selects a GPU product based on its memory, in megabytes (e.g. 4864)
# hours_remaining: (integer) The duration of the notebook in hours
#
# Example:
#
# settings = {
# 'notebook_name': 'MyNotebook',
# 'notebook_id': 'mynotebook',
# 'image': 'ml-platform:latest',
# 'owner': 'myusername',
# 'owner_uid': 2468,
# 'globus_id': 'alphanumeric string with hyphens',
# 'cpu_request': 1,
# 'cpu_limit': 2,
# 'memory_request': '1Gi',
# 'memory_limit': '2Gi',
# 'gpu_request': 1,
# 'gpu_limit': 1,
# 'gpu_memory': 4864,
# 'hours_remaining': 168
# }
# deploy_notebook(**settings)
def deploy_notebook(**settings):
    settings['namespace'] = namespace
    settings['token'] = b64encode(os.urandom(32)).decode()
    create_pod(**settings)
    create_service(**settings)
    create_ingress(**settings)
    create_secret(**settings)
    logger.info('Deployed notebook %s' %settings['notebook_name'])

# Function description: Looks up a notebook by name or by pod. Returns a dict.
#
# Function parameters:
# (Either a name or a pod is required to look up a notebook.)
#
# name: (string) The name of the notebook
# pod: (object) The pod object returned by the kubernetes client
# log: (boolean) When log is True, the function returns the pod log
# url: (boolean) When url is True, the function returns the notebook URL
# 
# Example #1:
#
# notebook = get_notebook(name='example-notebook')
#
# Example #2:
#
# pod = get_pod('example-notebook')
# notebook = get_notebook(pod=pod)
#
# Example #3:
#
# notebook = get_notebook(name='example-notebook', log=True, url=True)
def get_notebook(name=None, pod=None, log=False, url=False):
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
    notebook['status'] = get_notebook_status(pod)
    notebook['pod_status'] = pod.status.phase
    notebook['conditions'] = get_conditions(pod)
    notebook['events'] = get_events(pod)
    notebook['gpu'] = get_basic_gpu_info(pod)
    notebook['creation_date'] = pod.metadata.creation_timestamp.isoformat()
    notebook['expiration_date'] = get_expiration_date(pod).isoformat()
    notebook['hours_remaining'] = get_hours_remaining(pod)
    requests = pod.spec.containers[0].resources.requests
    notebook['requests'] = {
        'memory': requests['memory'][:-2] + ' GB',
        'cpu': int(requests['cpu']),
        'gpu': int(requests['nvidia.com/gpu'])
    }
    limits = pod.spec.containers[0].resources.limits
    notebook['limits'] = {
        'memory': limits['memory'][:-2] + ' GB',
        'cpu': int(limits['cpu']),
        'gpu': int(limits['nvidia.com/gpu'])
    }
    if log is True:
        notebook['log'] = api.read_namespaced_pod_log(name=name.lower(), namespace=namespace)
    if url is True:
        notebook['url'] = get_url(pod)
    return notebook

# Function description: Retrieves the notebooks for a specific owner, or for all users. Returns an array of dicts.
#
# Function parameters:
#
# owner: (string) The username of the owner. When owner is None, the function returns all notebooks for all users.
#
# Example #1:
# 
# notebooks = get_notebooks(owner='testuser2468') # returns all notebooks for user testuser2468
#
# Example #2:
#
# notebooks = get_notebooks() # returns all notebooks for all users
def get_notebooks(owner=None):
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

# Returns a list of the names of all notebooks in the namespace.
def list_notebooks():
    notebooks = []
    api = client.CoreV1Api()
    pods = api.list_namespaced_pod(namespace=namespace, label_selector='k8s-app=jupyterlab').items
    for pod in pods:
        notebooks.append(pod.metadata.name)
    return notebooks

# Removes a notebook from the namespace, and all Kubernetes objects associated with the notebook.
def remove_notebook(notebook_name):
    notebook_id = notebook_name.lower()
    core_v1_api = client.CoreV1Api()
    core_v1_api.delete_namespaced_pod(notebook_id, namespace)
    core_v1_api.delete_namespaced_service(notebook_id, namespace)
    core_v1_api.delete_namespaced_secret(notebook_id, namespace)
    networking_v1_api = client.NetworkingV1Api()
    networking_v1_api.delete_namespaced_ingress(notebook_id, namespace)
    logger.info('Removed notebook %s from namespace %s' %(notebook_id, namespace))

# Returns a boolean indicating whether a notebook name is available for use.
def notebook_name_available(notebook_name):
    notebook_id = notebook_name.lower()
    core_v1_api = client.CoreV1Api()
    pods = core_v1_api.list_namespaced_pod(namespace, label_selector='notebook-id={0}'.format(notebook_id))
    return len(pods.items) == 0

# Returns a default notebook name that is available for use, e.g. testuser-notebook-3.
def generate_notebook_name(owner):
    for i in range(1, 20):
        notebook_name = f'{owner}-notebook-{i}'
        if notebook_name_available(notebook_name):
            return notebook_name
    return None

# Returns a tuple of Docker images that are supported by the JupyterLab service.
def supported_images():
    return ('hub.opensciencegrid.org/usatlas/ml-platform:latest', 'hub.opensciencegrid.org/usatlas/ml-platform:conda', 
            'hub.opensciencegrid.org/usatlas/ml-platform:julia', 'hub.opensciencegrid.org/usatlas/ml-platform:lava',
            'hub.opensciencegrid.org/usatlas/ml-platform:centos7-experimental')

# Returns an array of GPU products and their availability.
def get_gpus():
    gpus = dict()
    api = client.CoreV1Api()
    nodes = api.list_node(label_selector='gpu=true')
    for node in nodes.items:
        product = node.metadata.labels['nvidia.com/gpu.product']
        memory = int(node.metadata.labels['nvidia.com/gpu.memory'])
        count = int(node.metadata.labels['nvidia.com/gpu.count'])
        if product not in gpus:
            gpus[product] = dict(product=product, memory=memory, count=count, available=count)
        else:
            gpus[product]['count'] += count
            gpus[product]['available'] += count 
        gpu = gpus[product]
        pods = api.list_pod_for_all_namespaces(field_selector='spec.nodeName=%s' %node.metadata.name).items
        for pod in pods:
            requests = pod.spec.containers[0].resources.requests
            if requests:
                gpu['available'] -= int(requests.get('nvidia.com/gpu', 0))
        gpu['available'] = max(gpu['available'], 0)
    return sorted(gpus.values(), key=lambda gpu : gpu['memory'])

# Looks up a GPU product by its memory size. Returns its product info and availability.
def get_gpu(memory):
    gpu = dict()
    api = client.CoreV1Api()
    nodes=api.list_node(label_selector='gpu=true,nvidia.com/gpu.memory=%s' %memory)
    for node in nodes.items:
        product = node.metadata.labels['nvidia.com/gpu.product']
        memory = int(node.metadata.labels['nvidia.com/gpu.memory'])
        count = int(node.metadata.labels['nvidia.com/gpu.count'])
        if not gpu:
            gpu = dict(product=product, memory=memory, count=count, available=count)
        gpu['count'] += count
        gpu['available'] += count
        pods = api.list_pod_for_all_namespaces(field_selector='spec.nodeName=%s' %node.metadata.name).items
        for pod in pods:
            requests = pod.spec.containers[0].resources.requests
            if requests:
                gpu['available'] -= int(requests.get('nvidia.com/gpu', 0))
                gpu['available'] = max(gpu['available'], 0)
    return gpu

def get_pod(pod_name):
    api = client.CoreV1Api()
    return api.read_namespaced_pod(name=pod_name, namespace=namespace)

# Below are helper functions used by the main interface.

def create_pod(**settings):
    api = client.CoreV1Api()
    templates = Environment(loader=FileSystemLoader('portal/templates/jupyterlab'))
    template = templates.get_template('pod.yaml')
    pod = yaml.safe_load(template.render(**settings))                           
    api.create_namespaced_pod(namespace=namespace, body=pod)

def create_service(**settings):
    api = client.CoreV1Api()
    templates = Environment(loader=FileSystemLoader('portal/templates/jupyterlab'))
    template = templates.get_template('service.yaml')
    service = yaml.safe_load(template.render(
        notebook_id=settings['notebook_id'],
        namespace=namespace, 
        image=settings['image']))
    api.create_namespaced_service(namespace=namespace, body=service)

def create_ingress(**settings):
    api = client.NetworkingV1Api()
    templates = Environment(loader=FileSystemLoader('portal/templates/jupyterlab'))
    template = templates.get_template('ingress.yaml')
    ingress = yaml.safe_load(template.render(
        notebook_id=settings['notebook_id'],
        namespace=namespace, 
        domain_name=app.config['DOMAIN_NAME'], 
        owner=settings['owner'], 
        image=settings['image']))
    api.create_namespaced_ingress(namespace=namespace, body=ingress)

def create_secret(**settings):
    api = client.CoreV1Api()
    templates = Environment(loader=FileSystemLoader('portal/templates/jupyterlab'))
    template = templates.get_template('secret.yaml')
    sec = yaml.safe_load(template.render(
        notebook_id=settings['notebook_id'], 
        namespace=namespace, 
        owner=settings['owner'], 
        token=settings['token']))
    api.create_namespaced_secret(namespace=namespace, body=sec)

def get_expiration_date(pod):
    creation_date = pod.metadata.creation_timestamp
    duration = pod.metadata.labels['time2delete']
    pattern = re.compile(r'ttl-\d+')
    if pattern.match(duration):
        hours = int(duration.split('-')[1])
        expiration_date = creation_date + datetime.timedelta(hours=hours)
        return expiration_date
    return None

def get_hours_remaining(pod):
    exp_date = get_expiration_date(pod)
    diff = exp_date - datetime.datetime.now(timezone.utc)
    return int(diff.total_seconds() / 3600)

def get_basic_gpu_info(pod):
    if pod.spec.node_name:
        requests = pod.spec.containers[0].resources.requests
        if int(requests.get('nvidia.com/gpu', 0)) > 0:
            api = client.CoreV1Api()
            node = api.read_node(pod.spec.node_name)
            product = node.metadata.labels['nvidia.com/gpu.product']
            memory = str(float(node.metadata.labels['nvidia.com/gpu.memory'])/1000) + ' GB'
            return {'product': product, 'memory':  memory}
    return None

def get_notebook_status(pod):
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

def get_conditions(pod):
    conditions = []
    sortorder = {'PodScheduled': 0, 'Initialized': 1, 'ContainersReady': 2, 'Ready': 3}
    for cond in pod.status.conditions:
        conditions.append({'type': cond.type, 'status': cond.status, 'timestamp': cond.last_transition_time.isoformat()})
    return sorted(conditions, key=lambda condition : sortorder.get(condition['type']))
    
def get_events(pod):
    notebook_events = []
    api = client.CoreV1Api()
    events = api.list_namespaced_event(namespace=namespace, field_selector='involvedObject.uid=%s' %pod.metadata.uid).items
    for event in events:
        notebook_events.append({'message': event.message, 'timestamp': event.last_timestamp.isoformat()})
    return notebook_events

def get_url(pod):
    if pod.metadata.deletion_timestamp:
        return None
    notebook_id = pod.metadata.name
    api = client.CoreV1Api()
    token = api.read_namespaced_secret(notebook_id, namespace).data['token']
    return 'https://%s.%s?%s' %(notebook_id, app.config['DOMAIN_NAME'], urllib.parse.urlencode({'token': token}))