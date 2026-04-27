import * as k8s from "@kubernetes/client-node";

let _kc: k8s.KubeConfig | null = null;

function getKubeConfig(): k8s.KubeConfig {
  if (!_kc) {
    _kc = new k8s.KubeConfig();
    const kubeconfig = process.env.KUBECONFIG;
    if (kubeconfig) {
      _kc.loadFromFile(kubeconfig);
    } else {
      try {
        _kc.loadFromCluster();
      } catch {
        _kc.loadFromDefault();
      }
    }
  }
  return _kc;
}

export function getCoreV1Api(): k8s.CoreV1Api {
  return getKubeConfig().makeApiClient(k8s.CoreV1Api);
}

export function getNetworkingV1Api(): k8s.NetworkingV1Api {
  return getKubeConfig().makeApiClient(k8s.NetworkingV1Api);
}
