"""
This module supports the JupyterLab service

Functionality:
===============

1. The start_notebook_maintenance method starts a thread for removing expired notebooks
2. The deploy_notebook method lets a user deploy a notebook onto our Kubernetes cluster
3. The get_notebook function lets a user get data for a single notebook
4. The get_notebooks function lets a user get data for all of a user's notebooks
5. The remove_notebook function lets a user remove a notebook
6. The list_notebooks function returns a list of the names of all currently running notebooks
7. The get_gpu_availability function lets a user know which GPU products are available for use

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
>>> notebook = jupyterlab.get_notebook('example-notebook-1')
>>> pprint(notebook)

Example #2:

cd <path>/<to>/af-portal
python
>>> from portal import jupyterlab
>>> from pprint import pprint
>>> notebooks = jupyterlab.get_notebooks('my-username')
>>> pprint(notebooks)

Example #3:

cd <path>/<to>/af-portal
python
>>> from portal import jupyterlab
>>> from pprint import pprint
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
>>> avail = jupyterlab.get_gpu_availability()
>>> pprint(avail)
>>> gpu1 = jupyterlab.get_gpu_availability(product='NVIDIA-A100-SXM4-40GB')
>>> pprint(gpu1)
>>> gpu2 = jupyterlab.get_gpu_availability(memory=4864)
>>> pprint(gpu2)

Example #6:

cd <path>/<to>/af-portal
python
>>> from portal import jupyterlab
>>> jupyterlab.list_notebooks()
"""

import math
import yaml
import time
import datetime
import threading
import os
import re
import urllib
from base64 import b64encode
from jinja2 import Environment, FileSystemLoader
from kubernetes import client, config
from kubernetes.utils.quantity import parse_quantity
from portal import app, logger

namespace = app.config.get("NAMESPACE")
kubeconfig = app.config.get("KUBECONFIG")

if kubeconfig:
    config.load_kube_config(config_file=kubeconfig)
    logger.info("Loaded kubeconfig from file %s" % kubeconfig)
else:
    config.load_kube_config()
    logger.info("Loaded default kubeconfig file")


def start_notebook_maintenance():
    def inner():
        while True:
            api = client.CoreV1Api()
            pods = api.list_namespaced_pod(
                namespace, label_selector="k8s-app=jupyterlab"
            ).items
            for pod in pods:
                exp_date = get_expiration_date(pod)
                if exp_date and exp_date < datetime.datetime.now(datetime.timezone.utc):
                    logger.info("Notebook %s has expired" % pod.metadata.name)
                    remove_notebook(pod.metadata.name)
            time.sleep(1800)

    threading.Thread(target=inner).start()
    logger.info("Started notebook maintenance")


def deploy_notebook(**settings):
    """
    Deploys a Jupyter notebook on our Kubernetes cluster.

    Function parameters:
    (All settings are required.)

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
    gpu_product: (string) Selects a GPU product based on name
    hours_remaining: (integer) The duration of the notebook in hours
    """
    settings["namespace"] = namespace
    settings["domain_name"] = app.config["DOMAIN_NAME"]
    settings["token"] = b64encode(os.urandom(32)).decode()
    settings["start_script"] = "/ML_platform_tests/SetupPrivateJupyterLab.sh"
    settings["notebook_id"] = sanitize_k8s_pod_name(settings["notebook_id"])
    if settings["image"].count("oct_upgrade"):
        settings["start_script"] = "/ML_platform_tests/SetupJupyterLab.sh"
    templates = Environment(loader=FileSystemLoader("portal/templates/jupyterlab"))
    api = client.CoreV1Api()
    # Create a pod for the notebook (the notebook runs as a container inside the pod)
    template = templates.get_template("pod.yaml")
    pod = yaml.safe_load(template.render(**settings))
    api.create_namespaced_pod(namespace=namespace, body=pod)
    # Create a service for the pod
    template = templates.get_template("service.yaml")
    service = yaml.safe_load(template.render(**settings))
    api.create_namespaced_service(namespace=namespace, body=service)
    # Store the JupyterLab token in a secret
    template = templates.get_template("secret.yaml")
    secret = yaml.safe_load(template.render(**settings))
    api.create_namespaced_secret(namespace=namespace, body=secret)
    # Create an ingress for the service (gives the notebook its own domain name and public key certificate)
    api = client.NetworkingV1Api()
    template = templates.get_template("ingress.yaml")
    ingress = yaml.safe_load(template.render(**settings))
    api.create_namespaced_ingress(namespace=namespace, body=ingress)
    logger.info("Deployed notebook %s" % settings["notebook_name"])


def get_notebook(name=None, pod=None, **options):
    """
    Looks up a notebook by name or by pod. Returns a dict.

    Function parameters:
    (Either a name or a pod is required to look up a notebook.)

    name: (string) The name of the notebook
    pod: (object) The pod object returned by the kubernetes client
    log: (boolean) When log is True, the pod log is included in the dict that gets returned
    url: (boolean) When url is True, the notebook URL is included in the dict that gets returned
    """
    api = client.CoreV1Api()
    if pod is None:
        pod = api.read_namespaced_pod(name=name.lower(), namespace=namespace)
    notebook = dict()
    try:
        notebook["id"] = pod.metadata.name
        notebook["name"] = pod.metadata.labels.get("notebook-name")
        notebook["namespace"] = namespace
        notebook["owner"] = pod.metadata.labels.get("owner")
        notebook["image"] = pod.spec.containers[0].image
        notebook["node"] = pod.spec.node_name
        notebook["node_selector"] = pod.spec.node_selector
        notebook["pod_status"] = pod.status.phase
        notebook["creation_date"] = pod.metadata.creation_timestamp.isoformat()
        expiration_date = get_expiration_date(pod)
        time_remaining = expiration_date - datetime.datetime.now(datetime.timezone.utc)
        notebook["expiration_date"] = expiration_date.isoformat()
        notebook["hours_remaining"] = int(time_remaining.total_seconds() / 3600)
        notebook["requests"] = pod.spec.containers[0].resources.requests
        notebook["limits"] = pod.spec.containers[0].resources.limits
        notebook["conditions"] = [
            {
                "type": c.type,
                "status": c.status,
                "timestamp": c.last_transition_time.isoformat(),
            }
            for c in pod.status.conditions
        ]
        notebook["conditions"].sort(
            key=lambda cond: dict(
                PodScheduled=0, Initialized=1, PodReadyToStartContainers=2, ContainersReady=3, Ready=4
            ).get(cond["type"])
        )
        events = api.list_namespaced_event(
            namespace=namespace, field_selector="involvedObject.uid=%s" % pod.metadata.uid
        ).items
        notebook["events"] = [
            {
                "message": e.message,
                "timestamp": e.last_timestamp.isoformat() if e.last_timestamp else None,
            }
            for e in events
        ]
        if pod.spec.node_name:
            node = api.read_node(pod.spec.node_name)
            if node.metadata.labels.get("gpu") == "true":
                notebook["gpu"] = {
                    "product": node.metadata.labels["nvidia.com/gpu.product"],
                    "memory": node.metadata.labels["nvidia.com/gpu.memory"] + "Mi",
                }
        if pod.metadata.deletion_timestamp is None:
            if next(
                filter(
                    lambda c: c.type == "Ready" and c.status == "True",
                    pod.status.conditions,
                ),
                None,
            ):
                log = api.read_namespaced_pod_log(pod.metadata.name, namespace=namespace)
                notebook["status"] = (
                    "Ready"
                    if re.search("Jupyter.*is running at", log)
                    else "Starting notebook..."
                )
            else:
                notebook["status"] = "Pending"
        else:
            notebook["status"] = "Removing notebook..."
        # Optional fields
        if options.get("log") is True and "log" in locals():
            notebook["log"] = log
        if options.get("url") is True and pod.metadata.deletion_timestamp is None:
            token = api.read_namespaced_secret(pod.metadata.name, namespace).data["token"]
            notebook["url"] = "https://%s.%s?%s" % (
                pod.metadata.name,
                app.config["DOMAIN_NAME"],
                urllib.parse.urlencode({"token": token}),
            )
    except Exception as e:
        logger.error("Caught exception in creating notebook information: %s", e)
    return notebook


def get_notebooks(owner=None, **options):
    """
    Retrieves a user's notebooks, or the notebooks for all users. Returns an array of dicts.

    Function parameters:
    (All parameters are optional.)

    owner: (string) The username of the owner. When owner is None, the function returns all notebooks for all users.
    log: (boolean) When log is True, the pod log is included in the dict that gets returned
    url: (boolean) When url is True, the notebook URL is included in the dict that gets returned
    """
    notebooks = []
    api = client.CoreV1Api()
    pods = api.list_namespaced_pod(
        namespace,
        label_selector=(
            "k8s-app=jupyterlab"
            if owner is None
            else "k8s-app=jupyterlab,owner=%s" % owner
        ),
    ).items
    for pod in pods:
        try:
            notebook = get_notebook(pod=pod, **options)
            logger.info("Notebook: %s", notebook)
            notebooks.append(notebook)
        except Exception as err:
            logger.error(
                "Error adding notebook %s to array.\n%s" % (pod.metadata.name, str(err))
            )
    return notebooks


def list_notebooks():
    """Returns a list of the names of all notebooks in the namespace."""
    api = client.CoreV1Api()
    pods = api.list_namespaced_pod(
        namespace=namespace, label_selector="k8s-app=jupyterlab"
    ).items
    return [pod.metadata.name for pod in pods]


def remove_notebook(name):
    """Removes a notebook from the namespace, and all Kubernetes objects associated with the notebook."""
    try:
        id = name.lower()
        api = client.CoreV1Api()
        api.delete_namespaced_pod(id, namespace)
        api.delete_namespaced_service(id, namespace)
        api.delete_namespaced_secret(id, namespace)
        api = client.NetworkingV1Api()
        api.delete_namespaced_ingress(id, namespace)
        logger.info("Removed notebook %s from namespace %s" % (id, namespace))
        return True
    except Exception as err:
        logger.error(str(err))
        return False


def notebook_name_available(name):
    """Returns a boolean indicating whether a notebook name is available for use."""
    api = client.CoreV1Api()
    pods = api.list_namespaced_pod(
        namespace, field_selector="metadata.name={0}".format(name.lower())
    )
    return len(pods.items) == 0


def generate_notebook_name(owner):
    """Returns a default notebook name that is available for use, e.g. testuser-notebook-3."""
    for i in range(1, 20):
        notebook_name = f"{owner}-notebook-{i}"
        if notebook_name_available(notebook_name):
            return notebook_name
    return None


def supported_images():
    """Returns a tuple of Docker images that are supported by the JupyterLab service."""
    return (
        "hub.opensciencegrid.org/usatlas/ml-platform:latest",
        "hub.opensciencegrid.org/usatlas/ml-platform:conda",
        "hub.opensciencegrid.org/usatlas/ml-platform:julia",
        "hub.opensciencegrid.org/usatlas/ml-platform:lava",
        "hub.opensciencegrid.org/usatlas/ml-platform:centos-v2-docker",
        "hub.opensciencegrid.org/usatlas/analysis-dask-uc:main",
        "hub.opensciencegrid.org/usatlas/analysis-dask-uc:dev",
        "hub.opensciencegrid.org/usatlas/ml-platform:oct_upgrade",
    )


def get_gpu_availability(product=None, memory=None):
    """
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
    """
    gpus = dict()
    api = client.CoreV1Api()
    if product:
        nodes = api.list_node(
            label_selector="gpu=true,nvidia.com/gpu.product=%s" % product
        )
    elif memory:
        nodes = api.list_node(
            label_selector="gpu=true,nvidia.com/gpu.memory=%s" % memory
        )
    else:
        nodes = api.list_node(label_selector="nvidia.com/gpu.product")
    for node in nodes.items:
        product = node.metadata.labels["nvidia.com/gpu.product"]
        memory = int(node.metadata.labels["nvidia.com/gpu.memory"])
        count = int(node.metadata.labels["nvidia.com/gpu.count"])
        if product not in gpus:
            gpus[product] = dict(
                mem_request_max=0,
                cpu_request_max=0,
                product=product,
                memory=memory,
                count=count,
                total_requests=0,
            )
        else:
            gpus[product]["count"] += count
        gpu = gpus[product]
        pods = api.list_pod_for_all_namespaces(
            field_selector="spec.nodeName=%s,status.phase!=%s,status.phase!=%s"
            % (node.metadata.name, "Succeeded", "Failed")
        ).items
        mem_request = 0
        cpu_request = 0
        gpu_request = 0
        for pod in pods:
            for container in pod.spec.containers:
                requests = container.resources.requests
                if requests:
                    gpu["total_requests"] += int(requests.get("nvidia.com/gpu", 0))
                    gpu_request += int(requests.get("nvidia.com/gpu", 0))
                    mem_request += parse_quantity(requests.get("memory", 0))
                    cpu_request += parse_quantity(requests.get("cpu", 0))
        # count in max only when there are at least 1 gpu available. the limitation is this guard is only safe if the requested
        # gpu is not more than 1.
        if int(node.status.capacity["nvidia.com/gpu"]) > gpu_request:
            mem_request_max = math.floor(
                (parse_quantity(node.status.capacity["memory"]) - mem_request)
                / (1024 * 1024 * 1024)
            )
            cpu_request_max = math.floor(
                parse_quantity(node.status.capacity["cpu"]) - cpu_request
            )
            gpu["mem_request_max"] = (
                mem_request_max
                if mem_request_max > gpu["mem_request_max"]
                else gpu["mem_request_max"]
            )
            gpu["cpu_request_max"] = (
                cpu_request_max
                if cpu_request_max > gpu["cpu_request_max"]
                else gpu["cpu_request_max"]
            )
        gpu["available"] = max(gpu["count"] - gpu["total_requests"], 0)
    return sorted(gpus.values(), key=lambda gpu: gpu["memory"])


def get_expiration_date(pod):
    """Returns the expiration date of the pod."""
    pattern = re.compile(r"ttl-\d+")
    if pattern.match(pod.metadata.labels["time2delete"]):
        hours = int(pod.metadata.labels["time2delete"].split("-")[1])
        return pod.metadata.creation_timestamp + datetime.timedelta(hours=hours)
    return None


def get_pod(name):
    """Looks up a Kubernetes pod by its name and returns a pod object."""
    try:
        api = client.CoreV1Api()
        return api.read_namespaced_pod(name=name, namespace=namespace)
    except:
        return None

def sanitize_k8s_pod_name(name: str, max_length: int = 63) -> str:
    """
    Sanitize a string to be a valid Kubernetes pod name.

    - Converts to lowercase.
    - Replaces invalid characters with '-'.
    - Ensures it starts and ends with an alphanumeric character.
    - Trims to the maximum allowed length (default: 63).

    Parameters:
        name (str): The original pod name.
        max_length (int): Maximum allowed length for Kubernetes pod names (default: 63).

    Returns:
        str: A valid Kubernetes pod name.
    """
    # Convert to lowercase
    name = name.lower()

    # Replace invalid characters (anything other than lowercase letters, numbers, or '-') with '-'
    name = re.sub(r'[^a-z0-9-]', '-', name)

    # Remove leading or trailing hyphens
    name = name.strip('-')

    # Truncate to max length
    name = name[:max_length]

    # Ensure it doesn't end with a hyphen after truncation
    name = name.rstrip('-')

    # If the name is empty after sanitization, default to a valid name
    return name if name else "default-pod"
