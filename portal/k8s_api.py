from os import path
import yaml
from kubernetes import client, config
from notebook.auth.security import passwd
import pprint

def create_jupyter_notebook(password):
    config.load_kube_config()
    
    with open(path.join(path.dirname(__file__), "yaml/deployment.yaml")) as f:
        dep = yaml.safe_load(f)
        password_hash = passwd(password)
        dep['spec']['template']['spec']['containers'][0]['args']= ["start-notebook.sh", f"--NotebookApp.password='{password_hash}'"]
        k8s_apps_v1 = client.AppsV1Api()
        resp = k8s_apps_v1.create_namespaced_deployment(body=dep, namespace="rolyata")
        pprint.pprint(dep)
        print("Deployment created. status='%s'" % resp.metadata.name)

    with open(path.join(path.dirname(__file__), "yaml/service.yaml")) as f:
        service = yaml.safe_load(f)
        core_v1_api = client.CoreV1Api()
        resp = core_v1_api.create_namespaced_service(namespace="rolyata", body=service)

    with open(path.join(path.dirname(__file__), "yaml/ingress.yaml")) as f:
        ingress = yaml.safe_load(f)
        networking_v1_api = client.NetworkingV1Api()
        resp = networking_v1_api.create_namespaced_ingress(namespace="rolyata",body=ingress)
