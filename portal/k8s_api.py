import yaml
import time
import datetime
from datetime import timezone
import re
from jinja2 import Environment, FileSystemLoader, select_autoescape
from kubernetes import client, config
from notebook.auth.security import passwd
from portal import log_api
from portal import app

logger = log_api.get_logger()

def load_kube_config():
    try:
        filename = app.config.get('KUBECONFIG')
        if filename:
            logger.info("Loading kubeconfig from file %s" % filename)
            config.load_kube_config(config_file = filename)
        else:
            logger.info("Loading default kubeconfig file")
            config.load_kube_config()
    except:
        logger.info('Error reading kube config')

def create_jupyter_notebook(notebook_name, namespace, username, password, cpu, memory, image, time_duration):
    config.load_kube_config()
    core_v1_api = client.CoreV1Api()
    networking_v1_api = client.NetworkingV1Api()

    pods = core_v1_api.list_namespaced_pod(namespace, label_selector="instance=" + notebook_name)
    if pods and len(pods.items) > 0:
        return {'status': 'warning', 'message': 'The name %s is already taken in namespace %s' %(notebook_name, namespace)}

    if image in ['ivukotic/ml_platform_auto:latest', 'ivukotic/ml_platform_auto:conda']:
        try:
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

            return {'status': 'success', 'message': 'Successfully created notebook %s' %notebook_name}
        except:
            return {'status': 'warning', 'message': 'Error creating notebook %s' %notebook_name}

    elif image == 'jupyter/minimal-notebook:latest':
        try: 
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

            return {'status': 'success', 'message': 'Successfully created notebook %s' %notebook_name}
        except:
            return {'status': 'warning', 'message': 'Error creating notebook %s' %notebook_name}
    else: 
        return {'status': 'warning', 'message': 'Docker image %s is not supported' %image}

def get_creation_date(pod):
    try:
        return pod.metadata.creation_timestamp
    except:
        return None

def get_creation_datestr(pod):
    creation_date = get_creation_date(pod)
    if creation_date:
        return creation_date.strftime('%B %d %Y %I:%M:%S %p %Z')
    else:
        return 'Unknown'

def get_expiration_date(pod):
    try:
        if hasattr(pod.metadata, 'labels') and 'time2delete' in pod.metadata.labels:
            cr_ts = pod.metadata.creation_timestamp
            td_str = pod.metadata.labels['time2delete']
            pattern = re.compile(r"ttl-\d+")
            if pattern.match(td_str):
                td = int(td_str.split("-")[1])
                expiration_date = cr_ts + datetime.timedelta(td)
                return expiration_date
    except:
        logger.info('Error getting expiration date')
    return None

def get_expiration_datestr(pod):
    expiration_date = get_expiration_date(pod)
    if expiration_date:
        return expiration_date.strftime('%B %d %Y %I:%M:%S %p %Z')
    else:
        return 'Never'

def has_notebook_expired(pod):
    return datetime.datetime.now(timezone.utc) > get_expiration_date(pod)

def has_notebook_loaded(namespace, pod):
    try: 
        if pod.status.phase == 'Running':
            core_v1_api = client.CoreV1Api()
            log = core_v1_api.read_namespaced_pod_log(pod.metadata.name, namespace=namespace)
            if re.search("Jupyter Notebook.*is running at.*", log):
                return True
    except:
        logger.info('Error reading log for pod %s' %pod.metadata.name)
    return False

def get_jupyter_notebooks(namespace, username):
    config.load_kube_config() # temporary until bug with load_kube_config is fixed
    core_v1_api = client.CoreV1Api()
    networking_v1_api = client.NetworkingV1Api()
    
    user_pods = []
    try:
        pods = core_v1_api.list_namespaced_pod(namespace)
        logger.info("Read %d pods from namespace %s" %(len(pods.items), namespace))
        for pod in pods.items:
            try: 
                name = pod.metadata.name
                if pod.metadata.labels['owner'] != username: 
                    continue
                elif has_notebook_expired(pod):
                    remove_jupyter_notebook(namespace, name, username)    
                else:       
                    user_pods.append(pod)
            except:
                logger.info('Error processing pod %s' %pod.metadata.name)
    except:
        logger.info('Error getting pods')

    notebooks = []
    for pod in user_pods:
        try: 
            name = pod.metadata.name
            logger.info("Read name for pod %s" %name)
            try: 
                ingress = networking_v1_api.read_namespaced_ingress(name, namespace)
                url = 'https://' + ingress.spec.rules[0].host
            except:
                logger.info('Error reading ingress for pod %s' %name)
                continue
            creation_date = get_creation_datestr(pod)
            expiration_date = get_expiration_datestr(pod)
            status = pod.status.phase
            finished_loading = has_notebook_loaded(namespace, pod)
            notebooks.append(
                {'name': name, 
                'namespace': namespace, 
                'username': username,
                'cluster': 'uchicago-river', 
                'url': url,
                'status': status,
                'finished_loading': finished_loading,
                'creation_date': creation_date,
                'expiration_date': expiration_date}
            )
        except:
            logger.info('Error processing Jupyter notebook %s' %pod.metadata.name)
        
    return notebooks

def remove_jupyter_notebook(namespace, notebook_name, username):
    config.load_kube_config()
    core_v1_api = client.CoreV1Api()
    networking_v1_api = client.NetworkingV1Api()
    try:
        pod = core_v1_api.read_namespaced_pod(notebook_name, namespace)
        if pod.metadata.labels['owner'] == username:
            core_v1_api.delete_namespaced_pod(notebook_name, namespace)
            core_v1_api.delete_namespaced_service(notebook_name, namespace)
            networking_v1_api.delete_namespaced_ingress(notebook_name, namespace)
            return {'status': 'success', 'message': 'Successfully removed notebook %s' %notebook_name}
        else:
            return {'status': 'warning', 'message': 'Notebook %s does not belong to user %s' %(notebook_name, username)}
    except:
        logger.info(f"Error deleting pod {notebook_name} in namespace {namespace}")
        return {'status': 'warning', 'message': 'Error removing notebook %s' %notebook_name}