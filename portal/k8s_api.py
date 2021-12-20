from os import path
import yaml
from kubernetes import client, config

config_loaded = False

if not config_loaded:
    config.load_kube_config()
    config_loaded = True

def create_jupyter_notebook():
    create_deployment()
    create_ingress()

def create_deployment():
    with open(path.join(path.dirname(__file__), "yaml/deployment.yaml")) as f:
        dep = yaml.safe_load(f)
        k8s_apps_v1 = client.AppsV1Api()
        resp = k8s_apps_v1.create_namespaced_deployment(
            body=dep, namespace="default")
        print("Deployment created. status='%s'" % resp.metadata.name)

def create_ingress():
    with open(path.join(path.dirname(__file__), "yaml/ingress.yaml")) as f:
        ingress = yaml.safe_load(f)
        # session["unix_name"] or session["primary_identity"] can help set the host and namespace
        networking_v1_api = client.NetworkingV1Api()
        resp = networking_v1_api.create_namespaced_ingress(
            namespace="default",
            body=ingress
        )