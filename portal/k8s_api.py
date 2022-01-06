from os import path
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from kubernetes import client, config
from notebook.auth.security import passwd
import time
import datetime
import re
import pprint
import logging
from portal import log_api
from portal import app

logger = log_api.get_logger()

def load_kube_config():
    if app.config['KUBECONFIG']:
        filename = app.config['KUBECONFIG']
        logger.info("Loading kubeconfig from file %s" % filename)
        config.load_kube_config(config_file = filename)
    else:
        logger.info("Loading default kubeconfig file")
        config.load_kube_config()

def create_jupyter_notebook(notebook_name, namespace, username, password, cpu, memory, image, time_duration):
    core_v1_api = client.CoreV1Api()
    networking_v1_api = client.NetworkingV1Api()

    if image in ['ivukotic/ml_platform_auto:latest', 'ivukotic/ml_platform_auto:conda']:
        env = Environment(loader=FileSystemLoader("portal/yaml/ml-platform"), autoescape=select_autoescape())
        
        template = env.get_template("pod.yaml")
        pod = yaml.safe_load(template.render(namespace=namespace, notebook_name=notebook_name, username=username, password=password, cpu=cpu, memory=memory, image=image, days=time_duration))
        resp = core_v1_api.create_namespaced_pod(body=pod, namespace=namespace)
        logger.info(resp)
        logger.info("Pod created. status='%s'" % resp.metadata.name)

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
        pod = yaml.safe_load(template.render(namespace=namespace, notebook_name=notebook_name, username=username, password=password_hash, cpu=cpu, memory=memory, image=image))
        resp = core_v1_api.create_namespaced_pod(body=pod, namespace=namespace)
        logger.info(resp)
        logger.info("Pod created. status='%s'" % resp.metadata.name)

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

def get_status(namespace, pod):
    core_v1_api = client.CoreV1Api()
    # crt = pod.metadata.creation_timestamp
    # now = datetime.datetime.now(datetime.timezone.utc)
    # duration_seconds = (now-crt).total_seconds()
    log = core_v1_api.read_namespaced_pod_log(pod.metadata.name, namespace=namespace)
    running = re.search("Jupyter Notebook.*is running at.*", log)
    if pod.status.phase == 'Running' and running is not None:
        return 'Running'
    elif pod.status.phase == 'Running' and running is None:
        return 'Loading'
    else:
        return pod.status.phase

def get_jupyter_notebooks(namespace, username):
    core_v1_api = client.CoreV1Api()
    networking_v1_api = client.NetworkingV1Api()

    notebooks = []
    try:
        pods = core_v1_api.list_namespaced_pod(namespace)
        logger.info("Read %d pods from namespace %s" %(len(pods.items), namespace))
        for pod in pods.items:
            try: 
                if pod.metadata.labels['owner'] == username:
                    name = pod.metadata.name
                    logger.info("Read name for pod %s" %name)
                    ingress = networking_v1_api.read_namespaced_ingress(name, namespace)
                    logger.info("Read ingress for pod %s" %name)
                    url = 'https://' + ingress.spec.rules[0].host
                    creation_date = get_creation_date(pod)
                    logger.info("Read creation date for pod %s" %name)
                    expiry_date = get_expiry_date(pod)
                    logger.info("Read expiration date for pod %s" %name)
                    status = get_status(namespace, pod)
                    logger.info("Read status for pod %s" %name)
                    notebooks.append(
                        {'name': name, 
                        'namespace': namespace, 
                        'username': username,
                        'cluster':'uchicago-river', 
                        'url': url,
                        'status': status,
                        'creation_date': creation_date,
                        'expiry_date': expiry_date}
                    )
            except:
                logger.info('Error processing Jupyter notebook %s' %pod.metadata.name)
    except:
        logger.info('Error getting Jupyter notebooks')

    # if notebooks:
        # logger.info(notebooks)
        
    return notebooks

def remove_jupyter_notebook(namespace, notebook_name, username):
    core_v1_api = client.CoreV1Api()
    networking_v1_api = client.NetworkingV1Api()
    try:
        pod = core_v1_api.read_namespaced_pod(notebook_name, namespace)
        if pod.metadata.labels['owner'] == username:
            core_v1_api.delete_namespaced_pod(notebook_name, namespace)
            core_v1_api.delete_namespaced_service(notebook_name, namespace)
            networking_v1_api.delete_namespaced_ingress(notebook_name, namespace)
            return True
    except:
        logger.info(f"Error deleting pod {notebook_name} in namespace {namespace}")
        return False