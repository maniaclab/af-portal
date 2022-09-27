# This module supports the JupyterLab service.
# It has a main interface near the top, and helper functions below the main interface.

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

# The main interface of the module
def deploy_notebook(notebook_id, notebook_name, image, owner, globus_id, 
                    cpu_request, memory_request, gpu_request, cpu_limit, memory_limit, gpu_limit, 
                    gpu_memory, hours_remaining):
    token = b64encode(os.urandom(32)).decode()
    create_pod(notebook_id, notebook_name, image, owner, globus_id, 
                cpu_request, memory_request, gpu_request, cpu_limit, memory_limit, gpu_limit, gpu_memory, 
                hours_remaining, token)
    create_service(notebook_id, image)
    create_ingress(notebook_id, owner, image)
    create_secret(notebook_id, owner, token)
    logger.info('Deployed notebook %s' %notebook_name)

def get_notebooks(owner=None):
    notebooks = []
    api = client.CoreV1Api()
    label_selector = 'k8s-app in (jupyterlab, privatejupyter),owner=%s' %owner if owner else 'k8s-app in (jupyterlab, privatejupyter)'
    pods = api.list_namespaced_pod(namespace, label_selector=label_selector).items 
    for pod in pods:
        try:
            notebook = dict()
            notebook['id'] = pod.metadata.name
            notebook['name'] = pod.metadata.labels.get('notebook-name') or pod.metadata.labels.get('display-name')
            notebook['namespace'] = namespace
            notebook['owner'] = pod.metadata.labels.get('owner')
            notebook['status'] = get_notebook_status(pod)
            notebook['pod_status'] = pod.status.phase
            notebook['conditions'] = get_conditions(pod)
            notebook['requests'] = get_requests(pod)
            notebook['limits'] = get_limits(pod)
            notebook['gpu'] = get_basic_gpu_info(pod)
            notebook['url'] = get_url(pod)
            notebook['creation_date'] = pod.metadata.creation_timestamp.isoformat()
            notebook['expiration_date'] = get_expiration_date(pod).isoformat()
            notebook['hours_remaining'] = get_hours_remaining(pod)
            notebooks.append(notebook)
        except Exception as err:
            logger.error('Error adding notebook %s to notebook array.\n%s' %(pod.metadata.name, str(err)))
    return notebooks

def get_notebook(notebook_name):
    api = client.CoreV1Api()
    pod = api.read_namespaced_pod(name=notebook_name.lower(), namespace=namespace)
    notebook = dict()
    notebook['id'] = pod.metadata.name
    notebook['name'] = pod.metadata.labels.get('notebook-name') or pod.metadata.labels.get('display-name')
    notebook['namespace'] = namespace
    notebook['owner'] = pod.metadata.labels.get('owner')
    notebook['image'] = pod.spec.containers[0].image
    notebook['node'] = pod.spec.node_name
    notebook['status'] = get_notebook_status(pod)
    notebook['pod_status'] = pod.status.phase
    notebook['conditions'] = get_conditions(pod)
    notebook['events'] = get_events(pod)
    notebook['node_selector'] = pod.spec.node_selector
    notebook['requests'] = get_requests(pod)
    notebook['limits'] = get_limits(pod)
    notebook['gpu'] = get_basic_gpu_info(pod)
    notebook['log'] = api.read_namespaced_pod_log(name=notebook_name.lower(), namespace=namespace)
    notebook['url'] = get_url(pod)
    notebook['creation_date'] = pod.metadata.creation_timestamp.isoformat()
    notebook['expiration_date'] = get_expiration_date(pod).isoformat()
    notebook['hours_remaining'] = get_hours_remaining(pod)
    return notebook

def list_notebooks():
    notebooks = []
    api = client.CoreV1Api()
    pods = api.list_namespaced_pod(namespace=namespace, label_selector='k8s-app in (jupyterlab, privatejupyter)').items
    for pod in pods:
        notebooks.append(pod.metadata.name)
    return notebooks

def remove_notebook(notebook_name):
    notebook_id = notebook_name.lower()
    core_v1_api = client.CoreV1Api()
    networking_v1_api = client.NetworkingV1Api()
    core_v1_api.delete_namespaced_pod(notebook_id, namespace)
    core_v1_api.delete_namespaced_service(notebook_id, namespace)
    networking_v1_api.delete_namespaced_ingress(notebook_id, namespace)
    core_v1_api.delete_namespaced_secret(notebook_id, namespace)
    logger.info('Removed notebook %s from namespace %s' %(notebook_id, namespace))

def notebook_name_available(notebook_name):
    notebook_id = notebook_name.lower()
    core_v1_api = client.CoreV1Api()
    pods = core_v1_api.list_namespaced_pod(namespace, label_selector='notebook-id={0}'.format(notebook_id))
    return len(pods.items) == 0

def generate_notebook_name(owner):
    for i in range(1, 20):
        notebook_name = f'{owner}-notebook-{i}'
        if notebook_name_available(notebook_name):
            return notebook_name
    return None

def supported_images():
    return ['hub.opensciencegrid.org/usatlas/ml-platform:latest', 'hub.opensciencegrid.org/usatlas/ml-platform:conda',
            'hub.opensciencegrid.org/usatlas/ml-platform:julia', 'hub.opensciencegrid.org/usatlas/ml-platform:lava']

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

# Helper functions
def create_pod(notebook_id, notebook_name, image, owner, globus_id, 
                cpu_request, memory_request, gpu_request, cpu_limit, memory_limit, gpu_limit, gpu_memory, 
                hours_remaining, token):
    api = client.CoreV1Api()
    templates = Environment(loader=FileSystemLoader('portal/templates/jupyterlab'))
    template = templates.get_template('pod.yaml')
    pod = yaml.safe_load(template.render(
        notebook_id=notebook_id, 
        notebook_name=notebook_name,
        namespace=namespace, 
        owner=owner,
        globus_id=globus_id, 
        token=token, 
        cpu_request=cpu_request,
        memory_request=f'{memory_request}Gi',
        gpu_request=gpu_request,
        cpu_limit=cpu_limit, 
        memory_limit=f'{memory_limit}Gi', 
        gpu_limit=gpu_limit,
        gpu_memory=gpu_memory,
        image=image, 
        hours=hours_remaining))                           
    api.create_namespaced_pod(namespace=namespace, body=pod)

def create_service(notebook_id, image):
    api = client.CoreV1Api()
    templates = Environment(loader=FileSystemLoader('portal/templates/jupyterlab'))
    template = templates.get_template('service.yaml')
    service = yaml.safe_load(template.render(
        notebook_id=notebook_id,
        namespace=namespace, 
        image=image))
    api.create_namespaced_service(namespace=namespace, body=service)

def create_ingress(notebook_id, owner, image):
    api = client.NetworkingV1Api()
    templates = Environment(loader=FileSystemLoader('portal/templates/jupyterlab'))
    template = templates.get_template('ingress.yaml')
    ingress = yaml.safe_load(template.render(
        notebook_id=notebook_id,
        namespace=namespace, 
        domain_name=app.config['DOMAIN_NAME'], 
        owner=owner, 
        image=image))
    api.create_namespaced_ingress(namespace=namespace, body=ingress)

def create_secret(notebook_id, owner, token):
    api = client.CoreV1Api()
    templates = Environment(loader=FileSystemLoader('portal/templates/jupyterlab'))
    template = templates.get_template('secret.yaml')
    sec = yaml.safe_load(template.render(
        notebook_id=notebook_id, 
        namespace=namespace, 
        owner=owner, 
        token=token))
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
    now_date = datetime.datetime.now(timezone.utc)
    diff = exp_date - now_date
    return int(diff.total_seconds() / 3600)

def get_requests(pod):
    hash_map = dict()
    requests = pod.spec.containers[0].resources.requests
    if requests:
        hash_map['memory'] = requests.get('memory', '0Gi')[:-2] + ' GB'
        hash_map['cpu'] = int(requests.get('cpu', 0))
        hash_map['gpu'] = int(requests.get('nvidia.com/gpu', 0))
    return hash_map

def get_limits(pod):
    hash_map = dict()
    limits = pod.spec.containers[0].resources.limits
    if limits:
        hash_map['memory'] = limits.get('memory', '0Gi')[:-2] + ' GB'
        hash_map['cpu'] = int(limits.get('cpu', 0))
        hash_map['gpu'] = int(limits.get('nvidia.com/gpu', 0))
    return hash_map

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
    api = client.NetworkingV1Api()
    ingress = api.read_namespaced_ingress(notebook_id, namespace)
    api = client.CoreV1Api()
    token = api.read_namespaced_secret(notebook_id, namespace).data['token']
    return 'https://' + ingress.spec.rules[0].host + '?' + urllib.parse.urlencode({'token': token})