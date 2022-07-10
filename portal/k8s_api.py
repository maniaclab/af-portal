# This module is organized in the following way:
# At the beginning of the file there are helper functions used by the main interface
# Toward the end of the file, the main interface is presented and introduced by a comment
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

# A class of exceptions that lets us pass a detailed error message to the frontend
class k8sException(Exception):
    pass

# Configures Kubernetes by loading the config_file if present, or else the default settings
@app.before_first_request
def load_kube_config():
    try:
        config.load_kube_config(config_file = config_file)
        logger.info("Loaded kubeconfig from file %s" %config_file)
    except:
        config.load_kube_config()
        logger.info("Loaded default kubeconfig file")
    logger.info("Using namespace %s" %namespace)
    logger.info("Using domain name %s" %domain_name)

# Starts the notebook manager, which removes expired notebooks, and checks for expired notebooks
@app.before_first_request
def start_notebook_manager():
    def manage_notebooks():
        while True:
            pods = get_all_pods()
            for pod in pods:
                name = pod.metadata.name
                exp_date = get_expiration_date(pod)
                curr_time = datetime.datetime.now(timezone.utc)
                if exp_date and exp_date < curr_time:
                    logger.info("Notebook %s in namespace %s has expired" %(name, namespace))
                    remove_notebook(name)                        
            time.sleep(1800)
    maintenance_thread = threading.Thread(target=manage_notebooks)
    maintenance_thread.start()
    logger.info("Started k8s notebook manager")

# The methods below are helper functions 
def create_pod(notebook_id, display_name, username, globus_id, cpu, memory, gpu, gpu_memory, image, time_duration, token):
    try: 
        api = client.CoreV1Api()
        templates = Environment(loader=FileSystemLoader("portal/templates/k8s"))
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
                gpu_memory=gpu_memory,
                image=image, 
                hours=time_duration))                           
        api.create_namespaced_pod(namespace=namespace, body=pod)
    except Exception as err:
        logger.error('Error creating pod %s\n%s' %(notebook_id, str(err)))
        raise k8sException('Error creating pod %s' %notebook_id)

def create_service(notebook_id, image):
    try: 
        api = client.CoreV1Api()
        templates = Environment(loader=FileSystemLoader("portal/templates/k8s"))
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
        templates = Environment(loader=FileSystemLoader("portal/templates/k8s"))
        template = templates.get_template("ingress.yaml")
        ingress = yaml.safe_load(
            template.render(
                domain_name=domain_name, 
                namespace=namespace, 
                notebook_id=notebook_id,
                username=username, 
                image=image))
        api.create_namespaced_ingress(namespace=namespace,body=ingress)
    except:
        logger.error('Error creating ingress %s' %notebook_id)
        raise k8sException('Error creating ingress %s' %notebook_id)

def create_secret(notebook_id, username, token):
    try: 
        api = client.CoreV1Api()
        templates = Environment(loader=FileSystemLoader("portal/templates/k8s"))
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

def create_pvc_if_needed(username):
    try:
        api = client.CoreV1Api()
        templates = Environment(loader=FileSystemLoader("portal/templates/k8s"))
        if len(api.list_namespaced_persistent_volume_claim(namespace, label_selector=f"owner={username}").items) == 0:
            template = templates.get_template("pvc.yaml")
            pvc = yaml.safe_load(template.render(username=username, namespace=namespace))
            api.create_namespaced_persistent_volume_claim(namespace=namespace, body=pvc)
            logger.info('Created persistent volume claim for user %s' %username)
    except Exception as err:
        logger.error('Error creating persistent volume claim for user %s\n%s' %(username, str(err)))
        raise k8sException('Error creating persistent volume claim for user %s' %username)

def supports_image(image):
    images = [
        'ivukotic/ml_platform:latest', 
        'ivukotic/ml_julia:latest', 
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
        return len(pods.items) == 0
    except:
        logger.error('Error checking whether notebook name %s is available' %notebook_id)
        raise k8sException('Error checking whether notebook name %s is available' %notebook_id)

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

def validate(notebook_name, notebook_id, username, cpu, memory, gpu, gpu_memory, image, time_duration):
    if " " in notebook_name:
        logger.warning('The name %s has whitespace' %notebook_name)
        raise k8sException('The notebook name cannot have any whitespace')

    if len(notebook_name) > 30:
        logger.warning('The name %s has more than 30 characters' %notebook_name)
        raise k8sException('The notebook name cannot exceed 30 characters')

    k8s_charset = set(string.ascii_lowercase + string.ascii_uppercase + string.digits + '_' + '-' + '.')

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
    return None

def get_creation_timestamp(pod):
    crt_date = get_creation_date(pod)
    if crt_date:
        return crt_date.timestamp()
    return -1

def get_expiration_timestamp(pod):
    exp_date = get_expiration_date(pod)
    if exp_date:
        return exp_date.timestamp()
    return -1

def get_hours_remaining(pod):
    exp_date = get_expiration_date(pod)
    if exp_date:
        now_date = datetime.datetime.now(timezone.utc)
        diff = exp_date - now_date
        return int(diff.total_seconds() / 3600)
    return -1

def pod_terminating(pod):
    if hasattr(pod.metadata, 'deletion_timestamp') and pod.metadata.deletion_timestamp:
        return True
    return False

def get_pod_status(pod):
    if pod_terminating(pod):
        return '--'
    return pod.status.phase

def get_certificate_status(pod):
    try:
        api = client.NetworkingV1Api()
        notebook_name = pod.metadata.name
        ingress = api.read_namespaced_ingress(notebook_name, namespace)
        secretName = ingress.spec.tls[0].secret_name
        objs = client.CustomObjectsApi()
        cert = objs.get_namespaced_custom_object(group="cert-manager.io", version="v1", name=secretName, namespace=namespace, plural="certificates")   
        for condition in cert['status']['conditions']:
            if condition['type'] == 'Ready':   
                if condition['status'] == 'True':
                    return 'Ready'
                else:
                    return 'Not ready' 
    except:
        logger.error("Error getting certificate status for notebook %s" %notebook_name)
    return 'Unknown'

def get_notebook_status(pod):
    pod_status = get_pod_status(pod)
    cert_status = get_certificate_status(pod)
    if pod_terminating(pod):
        return 'Removing notebook...'
    elif pod_status == 'Pending':
        return 'Pod starting...'
    elif cert_status != 'Ready':
        return 'Waiting for certificate...'
    elif pod_status == 'Running':
        try:
            core_v1_api = client.CoreV1Api()
            log = core_v1_api.read_namespaced_pod_log(pod.metadata.name, namespace=namespace)
            if re.search("Jupyter Notebook.*is running at.*", log) or re.search("Jupyter Server.*is running at.*", log):
                return 'Ready'
            else:
                return 'Notebook loading...'
        except: 
            return 'Error'
    else:
        return pod_status

def get_detailed_notebook_status(pod):
    if pod_terminating(pod):
        return None
    detailed_status = ['', '', '', '']
    for cond in pod.status.conditions:
        if cond.type == 'PodScheduled' and cond.status == 'True':
            detailed_status[0] = 'Pod scheduled.'
        elif cond.type == 'Initialized' and cond.status == 'True':
            detailed_status[1] = 'Pod initialized.'
        elif cond.type == 'Ready' and cond.status == 'True':
            detailed_status[2] = 'Pod ready.'
        elif cond.type == 'ContainersReady' and cond.status == 'True':
            detailed_status[3] = 'Containers ready.'
    cert_status = get_certificate_status(pod)
    if cert_status != 'Ready':
        detailed_status.append('Waiting for certificate...')
    nbstatus = get_notebook_status(pod)
    if nbstatus == 'Notebook loading...':
        detailed_status.append('Waiting for Jupyter notebook server...')
    elif nbstatus == 'Ready':
        detailed_status.append('Jupyter notebook server started.')
    return detailed_status

def get_token(notebook_name):
    try:
        api = client.CoreV1Api()
        sec = api.read_namespaced_secret(notebook_name, namespace)
        return sec.data['token']
    except:
        logger.error("Error getting secret for notebook %s" %notebook_name)

def get_display_name(pod):
    if hasattr(pod.metadata, 'labels') and 'display-name' in pod.metadata.labels:
        return pod.metadata.labels['display-name']
    return pod.metadata.name

def get_owner(pod):
    if hasattr(pod.metadata, 'labels') and 'owner' in pod.metadata.labels:
        return pod.metadata.labels['owner']
    return None

def get_url(pod):
    try: 
        if pod_terminating(pod):
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
        val = pod.spec.containers[0].resources.requests['memory']
        return val[:-2] + ' GB'
    except:
        logger.error('Error getting the memory request for a pod')   

def get_cpu_request(pod):
    try:
        return pod.spec.containers[0].resources.requests['cpu']
    except:
        logger.error('Error getting the CPU request for a pod')    

def get_gpu_request(pod):
    try:
        if 'nvidia.com/gpu' in pod.spec.containers[0].resources.requests:
            return pod.spec.containers[0].resources.requests['nvidia.com/gpu']
        return '0'
    except:
        logger.error('Error getting the GPU request for a pod')    

def get_gpu_memory_request(pod):
    try:
        if pod.spec.node_selector and 'nvidia.com/gpu.memory' in pod.spec.node_selector: 
            val = float(pod.spec.node_selector['nvidia.com/gpu.memory'])/1000
            return str(val) + ' GB'
        return '--'
    except:
        logger.error('Error getting the GPU memory request for a pod')

def get_pod(podname):
    try:
        core_v1_api = client.CoreV1Api()
        return core_v1_api.read_namespaced_pod(podname, namespace)
    except:
        logger.info('Pod %s does not exist' %podname)
        return None

def get_all_pods():
    try:
        core_v1_api = client.CoreV1Api()
        pods = core_v1_api.list_namespaced_pod(namespace, label_selector="k8s-app=privatejupyter")
        return pods.items
    except:
        logger.error('Error getting pods')
        return []

def get_user_pods(username):
    try:
        core_v1_api = client.CoreV1Api()
        user_pods = core_v1_api.list_namespaced_pod(namespace, label_selector=f"k8s-app=privatejupyter,owner={username}")       
        return user_pods.items
    except:
        logger.error('Error getting user pods')
        return []

# The methods below form the main interface of the k8s_api module
def create_notebook(notebook_name, username, globus_id, cpu, memory, gpu, gpu_memory, image, time_duration):
    notebook_id = notebook_name.lower()

    validate(notebook_name, notebook_id, username, cpu, memory, gpu, gpu_memory, image, time_duration)

    token_bytes = os.urandom(32)
    token = b64encode(token_bytes).decode()
    logger.info("The token for %s is %s" %(notebook_name, token))
      
    create_pod(notebook_id, notebook_name, username, globus_id, cpu, memory, gpu, gpu_memory, image, time_duration, token)
    create_service(notebook_id, image)
    create_ingress(notebook_id, username, image)
    create_secret(notebook_id, username, token)

    logger.info('Created notebook %s' %notebook_name)

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
            detailed_status = get_detailed_notebook_status(pod)
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
    pods = get_all_pods()
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
            core_v1_api.delete_namespaced_secret(notebook_id, namespace)
            logger.info('Removing notebook %s' %notebook_id)
        else:
            logger.warning('Notebook %s does not belong to user %s' %(notebook_id, username))
            raise k8sException('Notebook %s does not belong to user %s' %(notebook_id, username))
    except:
        logger.error(f"Error removing pod {notebook_id} in namespace {namespace}")
        raise k8sException('Error removing notebook %s' %notebook_id)

def remove_notebook(notebook_name):
    try: 
        notebook_id = notebook_name.lower()
        core_v1_api = client.CoreV1Api()
        networking_v1_api = client.NetworkingV1Api()
        core_v1_api.delete_namespaced_pod(notebook_id, namespace)
        core_v1_api.delete_namespaced_service(notebook_id, namespace)
        networking_v1_api.delete_namespaced_ingress(notebook_id, namespace)
        core_v1_api.delete_namespaced_secret(notebook_id, namespace)
        logger.info("Removed notebook %s in namespace %s" %(notebook_id, namespace))
    except: 
        logger.info('Error removing notebook %s during management cycle' %notebook_id) 

def get_autogenerated_notebook_name(username):
    try:
        for i in range(1, 100):
            nbname = f"{username}-notebook-{i}"
            if notebook_id_available(nbname):
                return nbname
    except:
        logger.error("Error getting autogenerated notebook name")
    return None