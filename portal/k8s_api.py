import yaml
import time
import datetime
import threading
from datetime import timezone
import re
from jinja2 import Environment, FileSystemLoader, select_autoescape
from kubernetes import client, config
from notebook.auth.security import passwd
from portal import logger
from portal import app

def load_kube_config():
    try:
        filename = app.config.get("KUBECONFIG")
        namespace = app.config.get("NAMESPACE")
        if filename:
            config.load_kube_config(config_file = filename)
            logger.info("Loaded kubeconfig from file %s" %filename)
            logger.info("Using namespace %s" %namespace)
        else:
            config.load_kube_config()
            logger.info("Loaded default kubeconfig file")
            logger.info("Using namespace %s" %namespace)
    except:
        logger.error("Error loading kubeconfig")
        config.load_kube_config()

def start_notebook_manager(namespace):
    t = threading.Thread(target=manage_notebooks, args=(namespace,))
    t.start()
    logger.info("Started k8s notebook manager")

def manage_notebooks(namespace):
    time.sleep(60)
    while True:
        pods = get_pods(namespace)
        count = 0
        for pod in pods:
            notebook_name = pod.metadata.name
            if has_notebook_expired(namespace, pod):
                logger.info("Notebook %s in namespace %s has expired" %(notebook_name, namespace))
                status = remove_notebook(namespace, notebook_name)
                if status:
                    count += 1
        logger.info("Removed %d notebooks during management cycle (1 cycle per hour)" %count)
        time.sleep(3600)


def create_notebook(notebook_name, namespace, username, password, cpu, memory, image, time_duration):
    core_v1_api = client.CoreV1Api()
    networking_v1_api = client.NetworkingV1Api()
    pods = core_v1_api.list_namespaced_pod(namespace, label_selector="instance=" + notebook_name)

    if pods and len(pods.items) > 0:
        logger.warning('The name %s is already taken in namespace %s' %(notebook_name, namespace))
        return {'status': 'warning', 'message': 'The name %s is already taken in namespace %s' %(notebook_name, namespace)}

    if image in ['ivukotic/ml_platform_auto:latest', 'ivukotic/ml_platform_auto:conda']:
        try:
            env = Environment(loader=FileSystemLoader("portal/yaml/ml-platform"), autoescape=select_autoescape())
            
            template = env.get_template("pod.yaml")
            pod = yaml.safe_load(template.render(namespace=namespace, notebook_name=notebook_name, username=username, password=password, cpu=cpu, memory=memory, image=image, days=time_duration))
            resp = core_v1_api.create_namespaced_pod(body=pod, namespace=namespace)

            template = env.get_template("service.yaml")
            service = yaml.safe_load(template.render(namespace=namespace, notebook_name=notebook_name))
            core_v1_api.create_namespaced_service(namespace=namespace, body=service)

            template = env.get_template("ingress.yaml")
            ingress = yaml.safe_load(template.render(namespace=namespace, notebook_name=notebook_name, username=username))
            networking_v1_api.create_namespaced_ingress(namespace=namespace,body=ingress)

            logger.info('Successfully created notebook %s' %notebook_name)
            return {'status': 'success', 'message': 'Successfully created notebook %s' %notebook_name}
        except:
            logger.error('Error creating notebook %s' %notebook_name)
            return {'status': 'warning', 'message': 'Error creating notebook %s' %notebook_name}

    elif image == 'jupyter/minimal-notebook:latest':
        try: 
            env = Environment(loader=FileSystemLoader("portal/yaml/minimal-notebook"), autoescape=select_autoescape())
            password_hash = passwd(password)

            template = env.get_template("pod.yaml")
            pod = yaml.safe_load(template.render(namespace=namespace, notebook_name=notebook_name, username=username, password=password_hash, cpu=cpu, memory=memory, image=image))
            resp = core_v1_api.create_namespaced_pod(body=pod, namespace=namespace)

            template = env.get_template("service.yaml")
            service = yaml.safe_load(template.render(namespace=namespace, notebook_name=notebook_name))
            core_v1_api.create_namespaced_service(namespace=namespace, body=service)

            template = env.get_template("ingress.yaml")
            ingress = yaml.safe_load(template.render(namespace=namespace, notebook_name=notebook_name, username=username))
            networking_v1_api.create_namespaced_ingress(namespace=namespace,body=ingress)

            logger.info('Successfully created notebook %s' %notebook_name)
            return {'status': 'success', 'message': 'Successfully created notebook %s' %notebook_name}
        except:
            logger.error('Error creating notebook %s' %notebook_name)
            return {'status': 'warning', 'message': 'Error creating notebook %s' %notebook_name}
    else: 
        return {'status': 'warning', 'message': 'Docker image %s is not supported' %image}

def get_creation_date(namespace, pod):
    try:
        return pod.metadata.creation_timestamp
    except:
        logger.error('Error getting creation date for notebook %s in namespace %s' %(pod.metadata.name, namespace))
        return None

def get_creation_timestamp(namespace, pod):
    creation_date = get_creation_date(namespace, pod)
    if creation_date:
        return creation_date.timestamp()
    return -1

def get_expiration_date(namespace, pod):
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
        logger.error('Error getting expiration date for notebook %s in namespace %s' %(pod.metadata.name, namespace))
    return None

def get_expiration_timestamp(namespace, pod):
    expiration_date = get_expiration_date(namespace, pod)
    if expiration_date:
        return expiration_date.timestamp()
    return -1

def has_notebook_expired(namespace, pod):
    exp_date = get_expiration_date(namespace, pod)
    if exp_date:
        return datetime.datetime.now(timezone.utc) > exp_date
    return False

def get_notebook_status(namespace, pod):
    try: 
        notebook_name = pod.metadata.name
        if pod.status.phase == 'Running':
            core_v1_api = client.CoreV1Api()
            log = core_v1_api.read_namespaced_pod_log(notebook_name, namespace=namespace)
            if re.search("Jupyter Notebook.*is running at.*", log):
                return 'Ready'
            else:
                return 'Loading'
    except:
        logger.error('Error getting status for notebook %s' %notebook_name)
    return 'Not ready'

def get_certificate_status(namespace, notebook_name):
    try:
        net = client.NetworkingV1Api()
        ingress = net.read_namespaced_ingress(notebook_name, namespace)
        secretName = ingress.spec.tls[0].secret_name
        objs = client.CustomObjectsApi()
        cert = objs.get_namespaced_custom_object(
            group = "cert-manager.io",
            version = "v1",
            name = secretName,
            namespace = namespace,
            plural = "certificates"
        )   
        for condition in cert['status']['conditions']:
            if condition['type'] == 'Ready':    
                return 'Ready' if condition['status'] == 'True' else 'Not ready'
    except:
        logger.error("Error getting certificate status for notebook %s" %notebook_name)
    return 'Unknown'

def get_url(namespace, notebook_name):
    try: 
        api = client.NetworkingV1Api()
        ingress = api.read_namespaced_ingress(notebook_name, namespace)
        # logger.info("Read ingress for pod %s" %notebook_name)
        url = 'https://' + ingress.spec.rules[0].host
        # logger.info('URL for pod %s: %s' %(notebook_name, url))
        return url
    except:
        logger.error('Error reading ingress for pod %s' %name)
        return ''

def get_pods(namespace):
    try:
        core_v1_api = client.CoreV1Api()
        pods = core_v1_api.list_namespaced_pod(namespace)
        logger.info("Read %d pods from namespace %s" %(len(pods.items), namespace))
        return pods.items
    except:
        return None

def get_user_pods(namespace, username):
    user_pods = []
    try:
        core_v1_api = client.CoreV1Api()
        pods = core_v1_api.list_namespaced_pod(namespace)
        for pod in pods.items:
            try: 
                if pod.metadata.labels['owner'] == username:     
                    user_pods.append(pod)
            except:
                logger.info('Error processing pod %s' %pod.metadata.name)
    except:
        logger.error('Error getting pods')
    logger.info("Read %d pods from namespace %s for user %s" %(len(user_pods), namespace, username))
    return user_pods

def get_notebooks(namespace, username):
    user_pods = get_user_pods(namespace, username)
    notebooks = []
    for pod in user_pods:
        try: 
            name = pod.metadata.name
            # logger.info("Read name for pod %s in namespace %s" %(name, namespace))
            url = get_url(namespace, name)
            # logger.info("Read URL for notebook %s" %name)
            creation_date = get_creation_timestamp(namespace, pod)
            # logger.info("Creation timestamp for notebook %s: %d" %(name, creation_date))
            expiration_date = get_expiration_timestamp(namespace, pod)
            # logger.info("Expiration timestamp for notebook %s: %d" %(name, expiration_date))
            pod_status = pod.status.phase
            # logger.info("Pod status for notebook %s: %s" %(name, pod_status))
            cert_status = get_certificate_status(namespace, name)
            # logger.info("Certificate status for notebook %s: %s" %(name, cert_status))
            notebook_status = get_notebook_status(namespace, pod)
            # logger.info("Notebook status for notebook %s: %s" %(name, notebook_status))
            notebooks.append(
                {'name': name, 
                'namespace': namespace, 
                'username': username,
                'url': url,
                'pod_status': pod_status,
                'cert_status': cert_status,
                'notebook_status': notebook_status,
                'creation_date': creation_date,
                'expiration_date': expiration_date}
            )
            logger.info("Retrieved notebook %s in namespace %s" %(name, namespace))
        except:
            logger.error('Error processing Jupyter notebook %s' %pod.metadata.name)
        
    return notebooks

def remove_notebook(namespace, notebook_name):
    try:
        core_v1_api = client.CoreV1Api()
        networking_v1_api = client.NetworkingV1Api()
        resp = core_v1_api.delete_namespaced_pod(notebook_name, namespace)
        logger.info(resp)
        core_v1_api.delete_namespaced_service(notebook_name, namespace)
        networking_v1_api.delete_namespaced_ingress(notebook_name, namespace)
        logger.info("Removed notebook %s in namespace %s" %(notebook_name, namespace))
        return True
    except:
        logger.error("Error removing notebook %s in namespace %s" %(notebook_name, namespace))
        return False

def remove_user_notebook(namespace, notebook_name, username):
    try:
        core_v1_api = client.CoreV1Api()
        networking_v1_api = client.NetworkingV1Api()
        pod = core_v1_api.read_namespaced_pod(notebook_name, namespace)
        if pod.metadata.labels['owner'] == username:
            core_v1_api.delete_namespaced_pod(notebook_name, namespace)
            core_v1_api.delete_namespaced_service(notebook_name, namespace)
            networking_v1_api.delete_namespaced_ingress(notebook_name, namespace)
            logger.info('Successfully removed notebook %s' %notebook_name)
            return {'status': 'success', 'message': 'Successfully removed notebook %s' %notebook_name}
        else:
            logger.warning('Notebook %s does not belong to user %s' %(notebook_name, username))
            return {'status': 'warning', 'message': 'Notebook %s does not belong to user %s' %(notebook_name, username)}
    except:
        logger.error(f"Error deleting pod {notebook_name} in namespace {namespace}")
        return {'status': 'warning', 'message': 'Error removing notebook %s' %notebook_name}