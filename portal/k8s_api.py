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
from jinja2 import Environment, FileSystemLoader, select_autoescape
from kubernetes import client, config
from portal import logger
from portal import app

templates = Environment(loader=FileSystemLoader("portal/yaml"), autoescape=select_autoescape())

namespace = app.config.get("NAMESPACE")
domain_name = app.config.get('DOMAIN_NAME')
ingress_class = app.config.get('INGRESS_CLASS')
gpu_available = app.config.get("GPU_AVAILABLE")
config_file = app.config.get("KUBECONFIG")

k8s_charset = set(string.ascii_lowercase + string.ascii_uppercase + string.digits + '_' + '-' + '.')

class k8sException(Exception):
    pass

def load_kube_config():
    try:
        if config_file:
            config.load_kube_config(config_file = config_file)
            logger.info("Loaded kubeconfig from file %s" %config_file)
        else:
            config.load_kube_config()
            logger.info("Loaded default kubeconfig file")
        logger.info("Using namespace %s" %namespace)
        logger.info("Using domain name %s" %domain_name)
        logger.info("GPU is available as a resource" if gpu_available else "GPU is not available as a resource")
        logger.info("Using kubernetes.io/ingress.class %s" %ingress_class)
    except:
        logger.error("Error loading kubeconfig")
        config.load_kube_config()

def start_notebook_manager():
    t = threading.Thread(target=manage_notebooks)
    t.start()
    logger.info("Started k8s notebook manager")

def manage_notebooks():
    time.sleep(10)
    while True:
        pods = get_pods()
        for pod in pods:
            if has_notebook_expired(pod):
                try:
                    logger.info("Notebook %s in namespace %s has expired" %(pod.metadata.name, namespace))
                    remove_notebook(pod.metadata.name)
                except:
                    logger.info('Error removing notebook %s during management cycle' %pod.metadata.name)
        time.sleep(1800)

def generate_token():
    token_bytes = os.urandom(32)
    b64_encoded = b64encode(token_bytes).decode()
    return b64_encoded

def create_pod(notebook_id, display_name, username, globus_id, cpu, memory, gpu, gpu_memory, image, time_duration, token):
    try: 
        api = client.CoreV1Api()
        template = templates.get_template("pod.yaml")
        cpu_limit = cpu * 2
        memory_limit = memory * 2
        pod = yaml.safe_load(
            template.render(
                namespace=namespace, 
                notebook_id=notebook_id, 
                display_name=display_name,
                username=username,
                globus_id=globus_id, 
                token=token, 
                cpu_request=cpu,
                cpu_limit=cpu_limit, 
                memory_request=f"{memory}Gi",
                memory_limit=f"{memory_limit}Gi", 
                gpu_request=gpu,
                gpu_limit=gpu,
                gpu_available=gpu_available, 
                gpu_memory=gpu_memory,
                image=image, 
                days=time_duration))                           
        api.create_namespaced_pod(namespace=namespace, body=pod)
    except Exception as err:
        logger.error('Error creating pod %s' %notebook_id)
        logger.error(str(err))
        raise k8sException('Error creating pod %s' %notebook_id)

def create_service(notebook_id, image):
    try: 
        api = client.CoreV1Api()
        template = templates.get_template("service.yaml")
        service = yaml.safe_load(
            template.render(
                namespace=namespace, 
                notebook_id=notebook_id,
                image=image))
        api.create_namespaced_service(namespace=namespace, body=service)
    except:
        logger.error('Error creating service %s' %notebook_id)
        raise k8sException('Error creating service %s' %notebook_id)

def create_ingress(notebook_id, username, image):
    try: 
        api = client.NetworkingV1Api()
        template = templates.get_template("ingress.yaml")
        ingress = yaml.safe_load(
            template.render(
                domain_name=domain_name, 
                ingress_class=ingress_class, 
                namespace=namespace, 
                notebook_id=notebook_id,
                username=username, 
                image=image))
        api.create_namespaced_ingress(namespace=namespace,body=ingress)
    except:
        logger.error('Error creating ingress %s' %notebook_id)
        raise k8sException('Error creating ingres %s' %notebook_id)

def create_secret(notebook_id, username, token):
    try: 
        api = client.CoreV1Api()
        template = templates.get_template("secret.yaml")
        sec = yaml.safe_load(
            template.render(
                namespace=namespace, 
                notebook_id=notebook_id, 
                username=username, 
                token=token))
        api.create_namespaced_secret(namespace=namespace, body=sec)
    except:
        logger.error('Error creating secret %s' %notebook_id)
        raise k8sException('Error creating secret %s' %notebook_id)

def supports_image(image):
    images = [
        'ivukotic/ml_platform:latest', 
        'ivukotic/ml_platform:conda', 
        'ivukotic/ml_platform_auto:latest', 
        'ivukotic/ml_platform_auto:conda', 
        'hub.opensciencegrid.org/usatlas/ml-platform:latest',
        'hub.opensciencegrid.org/usatlas/ml-platform:conda'
    ]
    return image in images

def notebook_id_available(notebook_id):
    try: 
        core_v1_api = client.CoreV1Api()
        pods = core_v1_api.list_namespaced_pod(namespace, label_selector="instance={0}".format(notebook_id))

        if not pods or len(pods.items) == 0:
            return True
    except:
        logger.error('Error checking whether notebook name %s is available' %notebook_id)
        raise k8sException('Error checking whether notebook name %s is available' %notebook_id)

def cpu_request_valid(cpu):
    if cpu >=1 and cpu <= 4:
        return True
    return False

def memory_request_valid(memory):
    if memory >=1 and memory <= 16:
        return True
    return False

def gpu_request_valid(gpu):
    if gpu >=0 and gpu <= 7:
        return True
    return False

def validate(notebook_name, notebook_id, username, cpu, memory, gpu, gpu_memory, image, time_duration):
    if " " in notebook_name:
        logger.warning('The name %s has whitespace' %notebook_name)
        raise k8sException('The notebook name cannot have any whitespace')

    if len(notebook_name) > 30:
        logger.warning('The name %s has more than 30 characters' %notebook_name)
        raise k8sException('The notebook name cannot exceed 30 characters')

    if not set(notebook_name) <= k8s_charset:
        logger.warning('The name %s has invalid characters' %notebook_name)
        raise k8sException('Valid characters are a-zA-Z0-9 and ._-')

    if not supports_image(image):
        logger.warning('Docker image %s is not suppported' %image)
        raise k8sException('Docker image %s is not supported' %image)

    if not notebook_id_available(notebook_id):
        logger.warning('The name %s is already taken' %notebook_name)
        raise k8sException('The name %s is already taken' %notebook_name)

    if not cpu_request_valid(cpu):
        logger.warning('The request of %d CPUs is outside the bounds [1, 4]' %cpu)
        raise k8sException('The request of %d CPUs is outside the bounds [1, 4]' %cpu)

    if not memory_request_valid(memory):
        logger.warning('The request of %d GB is outside the bounds [1, 16]' %memory)
        return k8sException('The request of %d GB is outside the bounds [1, 16]' %memory)

    if not gpu_request_valid(gpu):
        logger.warning('The request of %d GPUs is outside the bounds [1, 7]' %gpu)
        raise k8sException('The request of %d GPUs is outside the bounds [1, 7]' %gpu)

    if not gpu_memory or gpu_memory not in (4864, 40536):
        logger.warning('The gpu_memory value has to be 4864 or 40536')
        raise k8sException('The gpu_memory value has to be 4864 or 40536')

def create_notebook(notebook_name, username, globus_id, cpu, memory, gpu, gpu_memory, image, time_duration):
    notebook_id = notebook_name.lower()

    validate(notebook_name, notebook_id, username, cpu, memory, gpu, gpu_memory, image, time_duration)

    token = generate_token()
    logger.info("The token for %s is %s" %(notebook_name, token))
      
    create_pod(notebook_id, notebook_name, username, globus_id, cpu, memory, gpu, gpu_memory, image, time_duration, token)
    create_service(notebook_id, image)
    create_ingress(notebook_id, username, image)
    create_secret(notebook_id, username, token)

    logger.info('Created notebook %s' %notebook_name)

def get_creation_date(pod):
    return pod.metadata.creation_timestamp

def get_expiration_date(pod):
    try:
        if hasattr(pod.metadata, 'labels') and 'time2delete' in pod.metadata.labels:
            creation_ts = pod.metadata.creation_timestamp
            duration = pod.metadata.labels['time2delete']
            pattern = re.compile(r"ttl-\d+")
            if pattern.match(duration):
                hours = int(duration.split("-")[1])
                expiration_date = creation_ts + datetime.timedelta(hours=hours)
                return expiration_date
    except:
        logger.error('Error getting expiration date for notebook %s in namespace %s' %(pod.metadata.name, namespace))

def get_creation_timestamp(pod):
    creation_date = get_creation_date(pod)
    if creation_date:
        return creation_date.timestamp()
    return -1

def get_expiration_timestamp(pod):
    expiration_date = get_expiration_date(pod)
    if expiration_date:
        return expiration_date.timestamp()
    return -1

def has_notebook_expired(pod):
    exp_date = get_expiration_date(pod)
    if exp_date:
        return datetime.datetime.now(timezone.utc) > exp_date
    return False

def get_hours_remaining(pod):
    try:
        exp_date = get_expiration_date(pod)
        now_date = datetime.datetime.now(timezone.utc)
        diff = exp_date - now_date
        return int(diff.total_seconds() / 3600)
    except:
        logger.error('Error getting the hours remaining')

def get_pod_status(pod):
    try:
        if notebook_closing(pod):
            return '--'
        return pod.status.phase
    except:
        logger.error('Error getting status for pod %s' %pod.metadata.name)

def get_certificate_status(pod):
    try:
        if notebook_closing(pod):
            return '--'
        net = client.NetworkingV1Api()
        notebook_name = pod.metadata.name
        ingress = net.read_namespaced_ingress(notebook_name, namespace)
        secretName = ingress.spec.tls[0].secret_name
        objs = client.CustomObjectsApi()
        cert = objs.get_namespaced_custom_object(group="cert-manager.io", version="v1", name=secretName, namespace=namespace, plural="certificates")   
        for condition in cert['status']['conditions']:
            if condition['type'] == 'Ready':    
                return 'Ready' if condition['status'] == 'True' else 'Not ready'
        return 'Unknown'
    except:
        logger.error("Error getting certificate status for notebook %s" %notebook_name)

def notebook_closing(pod):
    try:
        if pod.metadata.deletion_timestamp:
            return True
        return False
    except:
        logger.error('Error checking whether notebook is closing in pod %s' %pod.metadata.name)

def get_notebook_status(pod):
    try: 
        pod_status = get_pod_status(pod)
        cert_status = get_certificate_status(pod)
        if notebook_closing(pod):
            return 'Removing notebook...'
        elif pod_status == 'Pending':
            return 'Pod starting...'
        elif cert_status != 'Ready':
            return 'Waiting for certificate...'
        elif pod_status == 'Running':
            core_v1_api = client.CoreV1Api()
            log = core_v1_api.read_namespaced_pod_log(pod.metadata.name, namespace=namespace)
            if re.search("Jupyter Notebook.*is running at.*", log) or re.search("Jupyter Server.*is running at.*", log):
                return 'Ready'
            else:
                return 'Notebook loading...'
        else:
            return pod_status
    except:
        logger.error('Error getting status for notebook %s' %pod.metadata.name)
        return 'Error'

def get_detailed_status(pod):
    try:
        detailed_status = []
        for c in pod.status.conditions:
            detailed_status.append("%s: %s" %(c.type, c.status))
        return detailed_status
    except:
        logger.error("Error getting detailed status for pod %s" %pod.metadata.name)

def get_token(notebook_name):
    try:
        api = client.CoreV1Api()
        sec = api.read_namespaced_secret(notebook_name, namespace)
        return sec.data['token']
    except:
        logger.error("Error getting secret for notebook %s" %notebook_name)

def get_display_name(pod):
    try:
        if hasattr(pod.metadata, 'labels') and 'display-name' in pod.metadata.labels:
            return pod.metadata.labels['display-name']
        return pod.metadata.name
    except:
        logger.error('Error getting value for display-name in pod %s' %pod.metadata.name)

def get_owner(pod):
    try:
        return pod.metadata.labels['owner']
    except:
        logger.error('Error getting value for owner in pod %s' %pod.metadata.name)

def get_url(pod):
    try: 
        if notebook_closing(pod):
            return None
        api = client.NetworkingV1Api()
        notebook_name = pod.metadata.name
        ingress = api.read_namespaced_ingress(notebook_name, namespace)
        token = get_token(notebook_name)
        url = 'https://' + ingress.spec.rules[0].host + '?' + urllib.parse.urlencode({'token': token})
        return url
    except:
        logger.error('Error getting URL for pod %s' %notebook_name)

def get_memory_request(pod):
    try:
        return pod.spec.containers[0].resources.requests['memory']
    except:
        logger.error('Error getting the memory request for a pod')   

def get_cpu_request(pod):
    try:
        return pod.spec.containers[0].resources.requests['cpu']
    except:
        logger.error('Error getting the CPU request for a pod')    

def get_gpu_request(pod):
    try:
        return pod.spec.containers[0].resources.requests['nvidia.com/gpu']
    except:
        logger.error('Error getting the GPU request for a pod')     

def get_gpu_memory_request(pod):
    try: 
        return pod.spec.node_selector['nvidia.com/gpu.memory'] + 'Mi'
    except:
        logger.error('Error getting the GPU memory request for a pod')

def get_pods():
    try:
        core_v1_api = client.CoreV1Api()
        pods = core_v1_api.list_namespaced_pod(namespace)
        return pods.items
    except:
        logger.error('Error getting pods')
        return []

def get_user_pods(username):
    try:
        user_pods = []
        core_v1_api = client.CoreV1Api()
        pods = core_v1_api.list_namespaced_pod(namespace)
        for pod in pods.items:
            try: 
                if pod.metadata.labels['owner'] == username:   
                    user_pods.append(pod)
            except:
                logger.error('Error processing pod %s' %pod.metadata.name)
        return user_pods        
    except:
        logger.error('Error getting user pods')
        return []

def get_notebooks(username):
    user_pods = get_user_pods(username)
    notebooks = []
    for pod in user_pods:
        try: 
            name = pod.metadata.name
            display_name = get_display_name(pod)
            url = get_url(pod)
            creation_date = get_creation_timestamp(pod)
            expiration_date = get_expiration_timestamp(pod)
            pod_status = get_pod_status(pod)
            cert_status = get_certificate_status(pod)
            notebook_status = get_notebook_status(pod)
            detailed_status = get_detailed_status(pod)
            memory_request = get_memory_request(pod)
            cpu_request = get_cpu_request(pod)
            gpu_request = get_gpu_request(pod)
            gpu_memory_request = get_gpu_memory_request(pod)
            hours_remaining = get_hours_remaining(pod)
            notebooks.append(
                {'name': name, 
                'display_name': display_name,
                'namespace': namespace, 
                'username': username,
                'url': url,
                'pod_status': pod_status,
                'cert_status': cert_status,
                'notebook_status': notebook_status,
                'detailed_status': detailed_status,
                'creation_date': creation_date,
                'expiration_date': expiration_date,
                'memory_request': memory_request,
                'cpu_request': cpu_request,
                'gpu_request': gpu_request,
                'gpu_memory_request': gpu_memory_request,
                'hours_remaining': hours_remaining}
            )
        except:          
            logger.error('Error processing Jupyter notebook %s' %pod.metadata.name)   
    return notebooks

def get_all_notebooks():
    pods = get_pods()
    notebooks = []
    for pod in pods:
        try: 
            name = pod.metadata.name
            display_name = get_display_name(pod)
            owner = get_owner(pod)
            url = get_url(pod)
            creation_date = get_creation_timestamp(pod)
            expiration_date = get_expiration_timestamp(pod)
            pod_status = get_pod_status(pod)
            cert_status = get_certificate_status(pod)
            notebook_status = get_notebook_status(pod)
            memory_request = get_memory_request(pod)
            cpu_request = get_cpu_request(pod)
            gpu_request = get_gpu_request(pod)
            gpu_memory_request = get_gpu_memory_request(pod)
            hours_remaining = get_hours_remaining(pod)
            notebooks.append(
                {'name': name, 
                'display_name': display_name,
                'namespace': namespace, 
                'username': owner,
                'url': url,
                'pod_status': pod_status,
                'cert_status': cert_status,
                'notebook_status': notebook_status,
                'creation_date': creation_date,
                'expiration_date': expiration_date,
                'memory_request': memory_request,
                'cpu_request': cpu_request,
                'gpu_request': gpu_request,
                'gpu_memory_request': gpu_memory_request,
                'hours_remaining': hours_remaining}
            )
        except:          
            logger.error('Error processing Jupyter notebook %s' %pod.metadata.name)   
    return notebooks

def remove_notebook(notebook_id):
    core_v1_api = client.CoreV1Api()
    core_v1_api.delete_namespaced_pod(notebook_id, namespace)
    core_v1_api.delete_namespaced_service(notebook_id, namespace)
    networking_v1_api = client.NetworkingV1Api()
    networking_v1_api.delete_namespaced_ingress(notebook_id, namespace)
    logger.info("Removing notebook %s in namespace %s" %(notebook_id, namespace))

def remove_user_notebook(notebook_name, username):
    try:
        notebook_id = notebook_name.lower()
        core_v1_api = client.CoreV1Api()
        networking_v1_api = client.NetworkingV1Api()
        pod = core_v1_api.read_namespaced_pod(notebook_id, namespace)
        if pod.metadata.labels['owner'] == username:
            core_v1_api.delete_namespaced_pod(notebook_id, namespace)
            core_v1_api.delete_namespaced_service(notebook_id, namespace)
            networking_v1_api.delete_namespaced_ingress(notebook_id, namespace)
            logger.info('Removing notebook %s' %notebook_id)
        else:
            logger.warning('Notebook %s does not belong to user %s' %(notebook_id, username))
            raise k8sException('Notebook %s does not belong to user %s' %(notebook_id, username))
    except:
        logger.error(f"Error removing pod {notebook_id} in namespace {namespace}")
        raise k8sException('Error removing notebook %s' %notebook_id)