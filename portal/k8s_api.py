from os import path
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from kubernetes import client, config
from notebook.auth.security import passwd
import datetime
import re
import pprint
import logging

logger = logging.getLogger("ciconnect-portal")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
fh = logging.FileHandler('ciconnect-portal.log')
fh.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s;%(levelname)s;%(message)s")
ch.setFormatter(formatter)
fh.setFormatter(formatter)
logger.addHandler(ch)
logger.addHandler(fh)

def create_jupyter_notebook(notebook_name, namespace, password, cpu, memory, image, time_duration):
    config.load_kube_config()
    core_v1_api = client.CoreV1Api()
    networking_v1_api = client.NetworkingV1Api()

    if image in ['ivukotic/ml_platform_auto:latest', 'ivukotic/ml_platform_auto:conda']:
        env = Environment(loader=FileSystemLoader("portal/yaml/ml-platform"), autoescape=select_autoescape())
        
        template = env.get_template("pod.yaml")
        pod = yaml.safe_load(template.render(namespace=namespace, notebook_name=notebook_name, password=password, cpu=cpu, memory=memory, image=image, days=time_duration))
        resp = core_v1_api.create_namespaced_pod(body=pod, namespace=namespace)
        pprint.pprint(resp)
        print("Pod created. status='%s'" % resp.metadata.name)

        template = env.get_template("service.yaml")
        service = yaml.safe_load(template.render(namespace=namespace, notebook_name=notebook_name))
        core_v1_api.create_namespaced_service(namespace=namespace, body=service)

        template = env.get_template("ingress.yaml")
        ingress = yaml.safe_load(template.render(namespace=namespace, notebook_name=notebook_name))
        networking_v1_api.create_namespaced_ingress(namespace=namespace,body=ingress)

    elif image == 'jupyter/minimal-notebook:latest':
        env = Environment(loader=FileSystemLoader("portal/yaml/minimal-notebook"), autoescape=select_autoescape())
        password_hash = passwd(password)

        template = env.get_template("pod.yaml")
        pod = yaml.safe_load(template.render(namespace=namespace, notebook_name=notebook_name, password=password_hash, cpu=cpu, memory=memory, image=image))
        resp = core_v1_api.create_namespaced_pod(body=pod, namespace=namespace)
        pprint.pprint(resp)
        print("Pod created. status='%s'" % resp.metadata.name)

        template = env.get_template("service.yaml")
        service = yaml.safe_load(template.render(namespace=namespace, notebook_name=notebook_name))
        core_v1_api.create_namespaced_service(namespace=namespace, body=service)

        template = env.get_template("ingress.yaml")
        ingress = yaml.safe_load(template.render(namespace=namespace, notebook_name=notebook_name))
        networking_v1_api.create_namespaced_ingress(namespace=namespace,body=ingress)

def get_creation_date(pod):
    try:
        return pod.metadata.creation_timestamp.strftime('%B %d %Y %I:%M:%S %p %Z')
    except:
        return 'Unknown'

def get_expiry_date(pod):
    try:
        if hasattr(pod.metadata, 'labels') and 'time2delete' in pod.metadata.labels:
            cr_ts = pod.metadata.creation_timestamp
            td_str = pod.metadata.labels['time2delete']
            valid = re.compile(r"ttl-\d+")
            if valid.match(td_str):
                td = int(td_str.split("-")[1])
                expiry_date = cr_ts + datetime.timedelta(td)
                return expiry_date.strftime('%B %d %Y %I:%M:%S %p %Z')
    except:
        logger.info('Error getting expiry date')
    return 'Never' 

def get_jupyter_notebooks(namespace):
    config.load_kube_config()
    core_v1_api = client.CoreV1Api()
    networking_v1_api = client.NetworkingV1Api()

    notebooks = []
    try:
        pods = core_v1_api.list_namespaced_pod(namespace)
        for pod in pods.items:
            name = pod.metadata.name
            ingress = networking_v1_api.read_namespaced_ingress(name, namespace)
            url = 'https://' + ingress.spec.rules[0].host
            creation_date = get_creation_date(pod)
            expiry_date = get_expiry_date(pod)
            notebooks.append(
                {'name': name, 
                'namespace': namespace, 
                'cluster':'uchicago-river', 
                'url': url,
                'creation_date': creation_date,
                'expiry_date': expiry_date}
            )
    except:
        logger.info('Error getting Jupyter notebooks')

    logger.info(notebooks)
    return notebooks

def remove_jupyter_notebook(namespace, notebook_name):
    config.load_kube_config()
    core_v1_api = client.CoreV1Api()
    networking_v1_api = client.NetworkingV1Api()
    try:
        core_v1_api.delete_namespaced_pod(notebook_name, namespace)
        core_v1_api.delete_namespaced_service(notebook_name, namespace)
        networking_v1_api.delete_namespaced_ingress(notebook_name, namespace)
        return True
    except:
        logger.info(f"Error deleting pod {notebook_name} in namespace {namespace}")
        return False