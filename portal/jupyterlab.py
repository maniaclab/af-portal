# This module supports the JupyterLab service
# It has a main interface near the top, and helper functions below the main interface

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

config_file = app.config.get("KUBECONFIG")
namespace = app.config.get("NAMESPACE")
domain_name = app.config.get("DOMAIN_NAME")

class JupyterLabException(Exception):
    pass

@app.before_first_request
def load_kube_config():
    if config_file:
        config.load_kube_config(config_file=config_file)
        logger.info("Loaded kubeconfig from file %s" %config_file)
    else:
        config.load_kube_config()
        logger.info("Loaded default kubeconfig file")

@app.before_first_request
def start_notebook_maintenance():
    def clean():
        while True:
            api = client.CoreV1Api()
            pods = api.list_namespaced_pod(namespace, label_selector="k8s-app=jupyterlab").items
            for pod in pods:
                notebook_name = pod.metadata.name
                exp_date = get_expiration_date(pod)
                now = datetime.datetime.now(timezone.utc)
                if exp_date and exp_date < now:
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
    create_pod(notebook_name, **kwargs)
    create_service(notebook_name, **kwargs)
    create_ingress(notebook_name, **kwargs)
    create_secret(notebook_name, **kwargs)
    logger.info("Created notebook %s" %notebook_name)

def get_notebooks(username=None):
    notebooks = []
    api = client.CoreV1Api()
    label_selector = "k8s-app=jupyterlab,owner=%s" %username if username else "k8s-app=jupyterlab"
    pods = api.list_namespaced_pod(namespace, label_selector=label_selector).items 
    for pod in pods:
        notebooks.append({
            "notebook_id": pod.metadata.name, 
            "notebook_name": pod.metadata.labels["notebook-name"],
            "namespace": namespace, 
            "username": pod.metadata.labels["owner"],
            "status": get_notebook_status(pod),
            "pod_status": pod.status.phase,
            "conditions": get_conditions(pod),
            "url": get_url(pod),
            "creation_date": pod.metadata.creation_timestamp.isoformat(),
            "expiration_date": get_expiration_date(pod).isoformat(),
            "requests": get_requests(pod),
            "limits": get_limits(pod),
            "gpu": get_gpu(pod),
            "hours_remaining": get_hours_remaining(pod)}) 
    return notebooks

def get_notebook(notebook_name):
    api = client.CoreV1Api()
    pod = api.read_namespaced_pod(name=notebook_name, namespace=namespace)
    log = api.read_namespaced_pod_log(name=notebook_name, namespace=namespace)
    notebook = {
        "notebook_id": pod.metadata.name,
        "notebook_name": pod.metadata.labels["notebook-name"],
        "namespace": namespace,
        "username": pod.metadata.labels["owner"],
        "image": pod.spec.containers[0].image,
        "node": pod.spec.node_name,
        "status": get_notebook_status(pod),
        "pod_status": pod.status.phase,
        "conditions": get_conditions(pod),
        "node_selector": pod.spec.node_selector,
        "events": get_events(pod),
        "log": log,
        "creation_date": pod.metadata.creation_timestamp.isoformat(),
        "expiration_date": get_expiration_date(pod).isoformat(),
        "requests": get_requests(pod),
        "limits": get_limits(pod),
        "gpu": get_gpu(pod),
        "hours_remaining": get_hours_remaining(pod),
    }
    return notebook

def list_notebooks():
    notebooks = []
    api = client.CoreV1Api()
    pods = api.list_namespaced_pod(namespace=namespace, label_selector="k8s-app=jupyterlab").items
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
    logger.info("Removed notebook %s from namespace %s" %(notebook_id, namespace))

def notebook_name_available(notebook_name):
    notebook_id = notebook_name.lower()
    core_v1_api = client.CoreV1Api()
    pods = core_v1_api.list_namespaced_pod(namespace, label_selector="notebook-id={0}".format(notebook_id))
    return len(pods.items) == 0

def generate_notebook_name(username):
    for i in range(1, 20):
        notebook_name = f"{username}-notebook-{i}"
        if notebook_name_available(notebook_name):
            return notebook_name
    return None

def supported_images():
    return [
        "hub.opensciencegrid.org/usatlas/ml-platform:latest",
        "hub.opensciencegrid.org/usatlas/ml-platform:conda",
        "hub.opensciencegrid.org/usatlas/ml-platform:julia",
        "hub.opensciencegrid.org/usatlas/ml-platform:lava"]

def get_gpus():
    gpus = dict()
    api = client.CoreV1Api()
    nodes = api.list_node(label_selector="gpu=true")
    for node in nodes.items:
        product = node.metadata.labels["nvidia.com/gpu.product"]
        memory = int(node.metadata.labels["nvidia.com/gpu.memory"])
        count = int(node.metadata.labels["nvidia.com/gpu.count"])
        if memory not in gpus:
            gpus[memory] = {"product": product, "memory": memory, "count": count, "available": count} 
        else:
            gpus[memory]["count"] += count
            gpus[memory]["available"] += count 
        gpu_requests = 0
        pods = api.list_namespaced_pod(namespace=namespace, field_selector="spec.nodeName=%s" %node.metadata.name).items
        for pod in pods:
            gpu_requests += int(pod.spec.containers[0].resources.requests.get("nvidia.com/gpu", 0))
        gpus[memory]["available"] = max(gpus[memory]["available"] - gpu_requests, 0)
    return sorted(gpus.values(), key=lambda gpu:gpu["memory"])

def validate(notebook_name, **kwargs):
    if " " in notebook_name:
        raise JupyterLabException("The notebook name cannot have any whitespace.")
    if len(notebook_name) > 30:
        raise JupyterLabException("The notebook name cannot exceed 30 characters.")
    k8s_charset = set(string.ascii_lowercase + string.ascii_uppercase + string.digits + "_" + "-" + ".")
    if not set(notebook_name) <= k8s_charset:
        raise JupyterLabException("Valid characters are [a-zA-Z0-9._-]")
    if not notebook_name_available(notebook_name):
        raise JupyterLabException("The name %s is already taken." %notebook_name)   
    if kwargs["image"] not in supported_images():
        raise JupyterLabException("Docker image %s is not supported." %kwargs["image"])
    if kwargs["cpu_request"] < 1 or kwargs["cpu_request"] > 4:
        raise JupyterLabException("The request of %d CPUs is outside the bounds [1, 4]." %kwargs["cpu_request"])
    if kwargs["memory_request"] < 0 or kwargs["memory_request"] > 16:
        return JupyterLabException("The request of %d GB is outside the bounds [1, 16]." %kwargs["memory_request"])
    if kwargs["gpu_request"] < 0 or kwargs["gpu_request"] > 7:
        raise JupyterLabException("The request of %d GPUs is outside the bounds [0, 7]." %kwargs["gpu_request"])
    gpus = get_gpus()
    gpu = next(filter(lambda gpu : gpu["memory"] == kwargs["gpu_memory"], gpus), None)
    if not gpu:
        raise JupyterLabException("The GPU product is not supported")
    if gpu["available"] < kwargs["gpu_request"]:
        raise JupyterLabException("The %s does not have %s %s available." 
            %(gpu["product"], kwargs["gpu_request"], "instance" if kwargs["gpu_request"] == 1 else "instances"))

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

def get_expiration_date(pod):
    creation_date = pod.metadata.creation_timestamp
    duration = pod.metadata.labels["time2delete"]
    pattern = re.compile(r"ttl-\d+")
    if pattern.match(duration):
        hours = int(duration.split("-")[1])
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
        hash_map["memory"] = requests.get("memory", "0Gi")[:-2] + " GB"
        hash_map["cpu"] = int(requests.get("cpu", 0))
        hash_map["gpu"] = int(requests.get("nvidia.com/gpu", 0))
    return hash_map

def get_limits(pod):
    hash_map = dict()
    limits = pod.spec.containers[0].resources.limits
    if limits:
        hash_map["memory"] = limits.get("memory", "0Gi")[:-2] + " GB"
        hash_map["cpu"] = int(limits.get("cpu", 0))
        hash_map["gpu"] = int(limits.get("nvidia.com/gpu", 0))
    return hash_map

def get_gpu(pod):
    if pod.spec.node_name:
        requests = pod.spec.containers[0].resources.requests
        if int(requests.get("nvidia.com/gpu", 0)) > 0:
            api = client.CoreV1Api()
            node = api.read_node(pod.spec.node_name)
            product = node.metadata.labels["nvidia.com/gpu.product"]
            memory = str(float(node.metadata.labels["nvidia.com/gpu.memory"])/1000) + " GB"
            return {"product": product, "memory":  memory}
    return None

def get_notebook_status(pod):
    if pod.metadata.deletion_timestamp:
        return "Removing notebook..."
    if pod.status.phase == "Running":
        api = client.CoreV1Api()
        log = api.read_namespaced_pod_log(pod.metadata.name, namespace=namespace)
        if re.search("Jupyter Notebook.*is running at", log) or re.search("Jupyter Server.*is running at", log):
            return "Ready"
        return "Starting notebook..."   
    return "Pending"

def get_conditions(pod):
    conditions = []
    sortorder = {"PodScheduled": 0, "Initialized": 1, "ContainersReady": 2, "Ready": 3}
    for cond in pod.status.conditions:
        conditions.append({"type": cond.type, "status": cond.status, "timestamp": cond.last_transition_time.isoformat()})
    return sorted(conditions, key=lambda condition : sortorder.get(condition["type"]))
    
def get_events(pod):
    notebook_events = []
    api = client.CoreV1Api()
    events = api.list_namespaced_event(namespace=namespace, field_selector="involvedObject.uid=%s" %pod.metadata.uid).items
    for event in events:
        notebook_events.append({"message": event.message, "timestamp": event.last_timestamp.isoformat()})
    return notebook_events

def get_url(pod):
    if pod.metadata.deletion_timestamp:
        return None
    notebook_id = pod.metadata.name
    api = client.NetworkingV1Api()
    ingress = api.read_namespaced_ingress(notebook_id, namespace)
    api = client.CoreV1Api()
    token = api.read_namespaced_secret(notebook_id, namespace).data["token"]
    return "https://" + ingress.spec.rules[0].host + "?" + urllib.parse.urlencode({"token": token})

def get_pod(pod_name):
    api = client.CoreV1Api()
    return api.read_namespaced_pod(name=pod_name, namespace=namespace)