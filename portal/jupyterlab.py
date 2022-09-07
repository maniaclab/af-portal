# This module is organized in the following way:
# The main interface is presented near the beginning of the file, at the create_notebook function.
# Beneath the main interface are helper functions used by the module.

import yaml
import time
import datetime
import threading
import os
import re
import string
import urllib
from base64 import b64encode
from datetime import timezone
from jinja2 import Environment, FileSystemLoader
from kubernetes import client, config
from portal import app, logger

# Kubernetes settings
config_file = app.config.get("KUBECONFIG")
namespace = app.config.get("NAMESPACE")
domain_name = app.config.get("DOMAIN_NAME")

# This exception provides the user with detailed error messages
class JupyterLabException(Exception):
    pass

# This function is called at the first HTTP request, before the request is processed
@app.before_first_request
def load_kube_config():
    if config_file:
        config.load_kube_config(config_file=config_file)
        logger.info("Loaded kubeconfig from file %s" %config_file)
    else:
        config.load_kube_config()
        logger.info("Loaded default kubeconfig file")

# Starts a thread that checks for expired notebooks and removes them
@app.before_first_request
def start_notebook_maintenance():
    def clean():
        while True:
            pods = get_all_pods()
            for pod in pods:
                notebook_name = pod.metadata.name
                exp_date = get_expiration_date(pod)
                curr_time = datetime.datetime.now(timezone.utc)
                if exp_date and exp_date < curr_time:
                    logger.info("Notebook %s has expired" %notebook_name)
                    remove_notebook(notebook_name)                        
            time.sleep(1800)
    threading.Thread(target=clean).start()
    logger.info("Started notebook maintenance")

# The main interface of the module
def create_notebook(notebook_name, **kwargs):
    validate(notebook_name, **kwargs)

    token_bytes = os.urandom(32)
    kwargs["token"] = b64encode(token_bytes).decode()
    logger.info("The token for %s is %s" %(notebook_name, kwargs["token"]))

    create_pod(notebook_name, **kwargs)
    create_service(notebook_name, **kwargs)
    create_ingress(notebook_name, **kwargs)
    create_secret(notebook_name, **kwargs)

    logger.info('Created notebook %s' %notebook_name)

def get_notebooks(username):
    user_pods = get_user_pods(username)
    notebooks = []
    for pod in user_pods:
        notebook_id = pod.metadata.name
        notebook_name = get_notebook_name(pod)
        status = get_notebook_status(pod)
        url = get_url(pod)
        creation_date = get_creation_date(pod)
        expiration_date = get_expiration_date(pod)
        memory_request = get_memory_request(pod)
        cpu_request = get_cpu_request(pod)
        gpu_request = get_gpu_request(pod)
        gpu_memory_request = get_gpu_memory_request(pod)
        hours_remaining = get_hours_remaining(pod)
        notebooks.append({
            'notebook_id': notebook_id, 
            'notebook_name': notebook_name,
            'namespace': namespace, 
            'username': username,
            'status': status,
            'url': url,
            'creation_date': creation_date.isoformat() if creation_date else "",
            'expiration_date': expiration_date.isoformat() if expiration_date else "",
            'memory_request': memory_request,
            'cpu_request': cpu_request,
            'gpu_request': gpu_request,
            'gpu_memory_request': gpu_memory_request,
            'hours_remaining': hours_remaining}) 
    return notebooks

def get_all_notebooks():
    pods = get_all_pods()
    notebooks = []
    for pod in pods:
        notebook_id = pod.metadata.name
        notebook_name = get_notebook_name(pod)
        username = get_owner(pod)
        status = get_notebook_status(pod)
        url = get_url(pod)
        creation_date = get_creation_date(pod)
        expiration_date = get_expiration_date(pod)
        memory_request = get_memory_request(pod)
        cpu_request = get_cpu_request(pod)
        gpu_request = get_gpu_request(pod)
        gpu_memory_request = get_gpu_memory_request(pod)
        hours_remaining = get_hours_remaining(pod)
        notebooks.append({
            'notebook_id': notebook_id, 
            'notebook_name': notebook_name,
            'namespace': namespace, 
            'username': username,
            'status': status,
            'url': url,
            'creation_date': creation_date.isoformat() if creation_date else "",
            'expiration_date': expiration_date.isoformat() if expiration_date else "",
            'memory_request': memory_request,
            'cpu_request': cpu_request,
            'gpu_request': gpu_request,
            'gpu_memory_request': gpu_memory_request,
            'hours_remaining': hours_remaining})
    return notebooks

def remove_notebook(notebook_name):
    notebook_id = notebook_name.lower()
    core_v1_api = client.CoreV1Api()
    networking_v1_api = client.NetworkingV1Api()
    core_v1_api.delete_namespaced_pod(notebook_id, namespace)
    core_v1_api.delete_namespaced_service(notebook_id, namespace)
    networking_v1_api.delete_namespaced_ingress(notebook_id, namespace)
    core_v1_api.delete_namespaced_secret(notebook_id, namespace)
    logger.info("Removed notebook %s from namespace %s" %(notebook_id, namespace))

def generate_notebook_name(username):
    for i in range(1, 20):
        nbname = f"{username}-notebook-{i}"
        if notebook_id_available(nbname):
            return nbname
    return None

def get_notebook_status(pod):
    notebook_status = {"current": "", "history": []}
    pod_status = get_pod_status(pod)
    if pod_status == "Closing":
        return {"current": "Removing notebook...", "history": []}

    messages = ["", "", "", ""]
    for cond in pod.status.conditions:
        if cond.type == "PodScheduled" and cond.status == "True":
            messages[0] = 'Pod scheduled.'
        elif cond.type == "Initialized" and cond.status == "True":
            messages[1] = "Pod initialized."
        elif cond.type == "Ready" and cond.status == "True":
            messages[2] = "Pod ready."
        elif cond.type == "ContainersReady" and cond.status == "True":
            messages[3] = "Containers ready."
        
    notebook_status["current"] = pod_status
    notebook_status["history"] = list(filter(None, messages))

    if pod_status == "Running":
        log = get_pod_log(pod)
        if re.search("Jupyter Notebook.*is running at", log) or re.search("Jupyter Server.*is running at", log):
            notebook_status["current"] = "Ready"
            notebook_status["history"].append("Jupyter notebook server started.")
        else:
            notebook_status["current"] = "Notebook loading..."
            notebook_status["history"].append("Waiting for Jupyter notebook server...")

    cert_status = get_certificate_status(pod)
    if cert_status != "Ready":
        notebook_status["current"] = "Waiting for certificate..."        

    return notebook_status

# Helper functions
def create_pod(notebook_name, **kwargs):
    api = client.CoreV1Api()
    templates = Environment(loader=FileSystemLoader("portal/templates/jupyterlab"))
    template = templates.get_template("pod.yaml")
    pod = yaml.safe_load(template.render(
        notebook_id=notebook_name.lower(), 
        notebook_name=notebook_name,
        namespace=namespace, 
        username=kwargs["username"],
        globus_id=kwargs["globus_id"], 
        token=kwargs["token"], 
        cpu_request=kwargs["cpu_request"],
        cpu_limit=kwargs["cpu_limit"], 
        memory_request=f'{kwargs["memory_request"]}Gi',
        memory_limit=f'{kwargs["memory_limit"]}Gi', 
        gpu_request=kwargs["gpu_request"],
        gpu_limit=kwargs["gpu_limit"],
        gpu_memory=kwargs["gpu_memory"],
        image=kwargs["image"], 
        hours=kwargs["duration"]))                           
    api.create_namespaced_pod(namespace=namespace, body=pod)

def create_service(notebook_name, **kwargs):
    api = client.CoreV1Api()
    templates = Environment(loader=FileSystemLoader("portal/templates/jupyterlab"))
    template = templates.get_template("service.yaml")
    service = yaml.safe_load(template.render(
        notebook_id=notebook_name.lower(),
        namespace=namespace, 
        image=kwargs["image"]))
    api.create_namespaced_service(namespace=namespace, body=service)

def create_ingress(notebook_name, **kwargs):
    api = client.NetworkingV1Api()
    templates = Environment(loader=FileSystemLoader("portal/templates/jupyterlab"))
    template = templates.get_template("ingress.yaml")
    ingress = yaml.safe_load(template.render(
        notebook_id=notebook_name.lower(),
        namespace=namespace, 
        domain_name=domain_name, 
        username=kwargs["username"], 
        image=kwargs["image"]))
    api.create_namespaced_ingress(namespace=namespace, body=ingress)

def create_secret(notebook_name, **kwargs):
    api = client.CoreV1Api()
    templates = Environment(loader=FileSystemLoader("portal/templates/jupyterlab"))
    template = templates.get_template("secret.yaml")
    sec = yaml.safe_load(template.render(
        notebook_id=notebook_name.lower(), 
        namespace=namespace, 
        username=kwargs["username"], 
        token=kwargs["token"]))
    api.create_namespaced_secret(namespace=namespace, body=sec)

def create_pvc_if_needed(username):
    api = client.CoreV1Api()
    templates = Environment(loader=FileSystemLoader("portal/templates/jupyterlab"))
    if len(api.list_namespaced_persistent_volume_claim(namespace, label_selector=f"owner={username}").items) == 0:
        template = templates.get_template("pvc.yaml")
        pvc = yaml.safe_load(template.render(username=username, namespace=namespace))
        api.create_namespaced_persistent_volume_claim(namespace=namespace, body=pvc)
        logger.info("Created persistent volume claim for user %s" %username)

def get_pod(notebook_name):
    notebook_id = notebook_name.lower()
    core_v1_api = client.CoreV1Api()
    return core_v1_api.read_namespaced_pod(notebook_id, namespace)

def get_all_pods():
    core_v1_api = client.CoreV1Api()
    pods = core_v1_api.list_namespaced_pod(namespace, label_selector="k8s-app=jupyterlab")
    return pods.items

def get_user_pods(username):
    core_v1_api = client.CoreV1Api()
    user_pods = core_v1_api.list_namespaced_pod(namespace, label_selector=f"k8s-app=jupyterlab,owner={username}")       
    return user_pods.items

def get_token(notebook_name):
    notebook_id = notebook_name.lower()
    api = client.CoreV1Api()
    return api.read_namespaced_secret(notebook_id, namespace).data["token"]

def supports_image(image):
    images = [
        "ivukotic/ml_platform:latest", 
        "ivukotic/ml_platform:conda", 
        "ivukotic/ml_julia:latest",
        "ivukotic/ml_platform_auto:latest", 
        "ivukotic/ml_platform_auto:conda", 
        "hub.opensciencegrid.org/usatlas/ml-platform:latest",
        "hub.opensciencegrid.org/usatlas/ml-platform:conda",
        "hub.opensciencegrid.org/usatlas/ml-platform:julia",
        "hub.opensciencegrid.org/usatlas/ml-platform:lava",
        "jupyter/minimal-notebook",
        "jupyter/scipy-notebook",
        "jupyter/datascience-notebook"
    ]
    return image in images

def notebook_id_available(notebook_name):
    notebook_id = notebook_name.lower()
    core_v1_api = client.CoreV1Api()
    pods = core_v1_api.list_namespaced_pod(namespace, label_selector="notebook-id={0}".format(notebook_id))
    return len(pods.items) == 0

def cpu_request_valid(cpu):
    if cpu >= 1 and cpu <= 4:
        return True
    return False

def memory_request_valid(memory):
    if memory >= 1 and memory <= 16:
        return True
    return False

def gpu_request_valid(gpu):
    if gpu >= 0 and gpu <= 7:
        return True
    return False

def validate(notebook_name, **kwargs):
    if " " in notebook_name:
        raise JupyterLabException("The notebook name cannot have any whitespace")

    if len(notebook_name) > 30:
        raise JupyterLabException("The notebook name cannot exceed 30 characters")

    k8s_charset = set(string.ascii_lowercase + string.ascii_uppercase + string.digits + "_" + "-" + ".")

    if not set(notebook_name) <= k8s_charset:
        raise JupyterLabException("Valid characters are a-zA-Z0-9 and ._-")

    if not notebook_id_available(notebook_name.lower()):
        raise JupyterLabException("The name %s is already taken" %notebook_name)   

    if not supports_image(kwargs["image"]):
        raise JupyterLabException('Docker image %s is not supported' %kwargs["image"])

    if not cpu_request_valid(kwargs["cpu_request"]):
        raise JupyterLabException('The request of %d CPUs is outside the bounds [1, 4]' %kwargs["cpu"])

    if not memory_request_valid(kwargs["memory_request"]):
        return JupyterLabException('The request of %d GB is outside the bounds [1, 16]' %kwargs["memory"])

    if not gpu_request_valid(kwargs["gpu_request"]):
        raise JupyterLabException("The request of %d GPUs is outside the bounds [1, 7]" %kwargs["gpu"])

    if not kwargs["gpu_memory"] or kwargs["gpu_memory"] not in [4864, 40536, 11019, 11178, 16160]:
        raise JupyterLabException("The gpu memory request is invalid.")

def get_creation_date(pod):
    return pod.metadata.creation_timestamp

def get_expiration_date(pod):
    creation_ts = pod.metadata.creation_timestamp
    duration = pod.metadata.labels["time2delete"]
    pattern = re.compile(r"ttl-\d+")
    if pattern.match(duration):
        hours = int(duration.split("-")[1])
        expiration_date = creation_ts + datetime.timedelta(hours=hours)
        return expiration_date
    return None

def get_hours_remaining(pod):
    exp_date = get_expiration_date(pod)
    now_date = datetime.datetime.now(timezone.utc)
    diff = exp_date - now_date
    return int(diff.total_seconds() / 3600)

def get_pod_status(pod):
    if pod.metadata.deletion_timestamp:
        return "Closing"
    return pod.status.phase

def get_pod_log(pod):
    api = client.CoreV1Api()
    return api.read_namespaced_pod_log(pod.metadata.name, namespace=namespace)

def get_certificate_status(pod):
    api = client.NetworkingV1Api()
    notebook_name = pod.metadata.name
    ingress = api.read_namespaced_ingress(notebook_name, namespace)
    secretName = ingress.spec.tls[0].secret_name
    objs = client.CustomObjectsApi()
    cert = objs.get_namespaced_custom_object(group="cert-manager.io", version="v1", name=secretName, namespace=namespace, plural="certificates")   
    for condition in cert["status"]["conditions"]:
        if condition["type"] == "Ready":   
            if condition["status"] == "True":
                return "Ready"
            else:
                return "Not ready"
    return "Unknown"

def get_notebook_name(pod):
    return pod.metadata.labels['notebook-name']

def get_owner(pod):
    return pod.metadata.labels['owner']

def get_url(pod):
    if get_pod_status(pod) == "Closing":
        return None
    api = client.NetworkingV1Api()
    notebook_id = pod.metadata.name
    ingress = api.read_namespaced_ingress(notebook_id, namespace)
    token = get_token(notebook_id)
    return "https://" + ingress.spec.rules[0].host + "?" + urllib.parse.urlencode({"token": token})

def get_memory_request(pod):
    return pod.spec.containers[0].resources.requests["memory"][:-2] + " GB"

def get_cpu_request(pod):
    return pod.spec.containers[0].resources.requests["cpu"] 

def get_gpu_request(pod):
    return pod.spec.containers[0].resources.requests["nvidia.com/gpu"]

def get_gpu_memory_request(pod):
    if pod.spec.node_selector and "nvidia.com/gpu.memory" in pod.spec.node_selector:
        return str(float(pod.spec.node_selector["nvidia.com/gpu.memory"])/1000) + " GB"
    return "0"

def get_gpu_products():
    gpus = dict()
    api = client.CoreV1Api()
    nodes = api.list_node(label_selector="gpu=true")
    for node in nodes.items:
        labels = node.metadata.labels
        product = labels["nvidia.com/gpu.product"]
        memory = labels["nvidia.com/gpu.memory"]
        if product not in gpus:
            count = int(labels["nvidia.com/gpu.count"])
            gpus[product] = {"product": product, "memory": memory, "count": count, "available": 0} 
        else:
            assert gpus[product]["memory"] == memory, "GPU %s does not have a unique memory size" %product
            gpus[product]["count"] += int(labels["nvidia.com/gpu.count"])
        pods = api.list_namespaced_pod(namespace=namespace, label_selector="gpu-memory=%s" %memory).items
        count = gpus[product]["count"]
        busy = 0 
        for pod in pods:
            busy += int(get_gpu_request(pod))
        if count - busy > 0:
            gpus[product]["available"] = count - busy
    return list(gpus.values())
