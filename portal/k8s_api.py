from os import path
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from kubernetes import client, config
from notebook.auth.security import passwd
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

def create_jupyter_notebook(notebook_name, namespace, password, cpu, memory, image):
    config.load_kube_config()
    core_v1_api = client.CoreV1Api()
    networking_v1_api = client.NetworkingV1Api()

    ml_setup = True if image in ['ivukotic/ml_platform_auto:latest', 'ivukotic/ml_platform_auto:conda'] else False
    yaml_dir = "portal/yaml/ml-platform" if ml_setup else "portal/yaml/minimal-notebook"
    password = password if ml_setup else passwd(password) 

    env = Environment(loader=FileSystemLoader(yaml_dir), autoescape=select_autoescape())

    template = env.get_template("pod.yaml")
    pod = yaml.safe_load(template.render(namespace=namespace, notebook_name=notebook_name, password=password, cpu=cpu, memory=memory, image=image))
    resp = core_v1_api.create_namespaced_pod(body=pod, namespace=namespace)
    pprint.pprint(resp)
    print("Pod created. status='%s'" % resp.metadata.name)

    template = env.get_template("service.yaml")
    service = yaml.safe_load(template.render(namespace=namespace, notebook_name=notebook_name))
    core_v1_api.create_namespaced_service(namespace=namespace, body=service)

    template = env.get_template("ingress.yaml")
    ingress = yaml.safe_load(template.render(namespace=namespace, notebook_name=notebook_name))
    networking_v1_api.create_namespaced_ingress(namespace=namespace,body=ingress)

def get_jupyter_notebooks(namespace):
    config.load_kube_config()
    networking_v1_api = client.NetworkingV1Api()
    ingresses = networking_v1_api.list_namespaced_ingress(namespace)
    notebooks = []
    try:
        for ingress in ingresses.items:
            notebooks.append(
                {'name': ingress.metadata.name, 
                'namespace': ingress.metadata.namespace, 
                'cluster':'uchicago-river', 
                'url': 'https://' + ingress.spec.rules[0].host}
            )
    except:
        logger.info('Error accessing ingress file')

    logger.info(notebooks)

    return notebooks

def remove_jupyter_notebook(namespace, notebook_name):
    config.load_kube_config()
    try:
        k8s_apps_v1 = client.AppsV1Api()
        k8s_apps_v1.delete_namespaced_deployment(namespace=namespace, name=notebook_name)
        core_v1_api = client.CoreV1Api()
        core_v1_api.delete_namespaced_service(namespace=namespace, name=notebook_name)
        networking_v1_api = client.NetworkingV1Api()
        networking_v1_api.delete_namespaced_ingress(namespace=namespace, name=notebook_name)
        return True
    except:
        return False