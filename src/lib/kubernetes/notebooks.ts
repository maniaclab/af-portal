import * as k8s from "@kubernetes/client-node";
import crypto from "crypto";
import { getCoreV1Api, getNetworkingV1Api } from "./client";
import { sanitizeK8sPodName } from "./utils";
import type { Notebook, GpuAvailability, DeployNotebookSettings } from "@/types";

const NAMESPACE = process.env.NAMESPACE ?? "af";
const DOMAIN_NAME = process.env.DOMAIN_NAME ?? "af.uchicago.edu";

export async function deployNotebook(
  settings: DeployNotebookSettings
): Promise<void> {
  const api = getCoreV1Api();
  const netApi = getNetworkingV1Api();

  const notebookId = sanitizeK8sPodName(settings.notebook_id);
  const token = crypto.randomBytes(32).toString("base64");
  const tokenB64 = Buffer.from(token).toString("base64");

  // --- Pod ---
  const pod: k8s.V1Pod = {
    apiVersion: "v1",
    kind: "Pod",
    metadata: {
      name: notebookId,
      namespace: NAMESPACE,
      labels: {
        "notebook-id": notebookId,
        "notebook-name": settings.notebook_name,
        "k8s-app": "jupyterlab",
        owner: settings.owner,
        "globus-id": settings.globus_id,
        time2delete: `ttl-${settings.hours_remaining}`,
      },
    },
    spec: {
      ...(settings.gpu_request > 0
        ? {
            nodeSelector: {
              "nvidia.com/gpu.product": settings.gpu_product,
            },
          }
        : {
            affinity: {
              nodeAffinity: {
                requiredDuringSchedulingIgnoredDuringExecution: {
                  nodeSelectorTerms: [
                    {
                      matchExpressions: [
                        {
                          key: "partition",
                          operator: "NotIn",
                          values: ["gpu"],
                        },
                      ],
                    },
                  ],
                },
                preferredDuringSchedulingIgnoredDuringExecution: [
                  {
                    weight: 10,
                    preference: {
                      matchExpressions: [
                        {
                          key: "partition",
                          operator: "In",
                          values: ["login"],
                        },
                      ],
                    },
                  },
                ],
              },
            },
            tolerations: [
              {
                key: "hub.jupyter.org/dedicated",
                operator: "Exists",
                effect: "NoSchedule",
              },
            ],
          }),
      restartPolicy: "Always",
      containers: [
        {
          name: notebookId,
          image: settings.image,
          imagePullPolicy: "Always",
          args: ["/usr/local/bin/SetupPrivateJupyterLab.sh"],
          env: [
            { name: "JUPYTER_TOKEN", value: token },
            {
              name: "API_TOKEN",
              valueFrom: {
                secretKeyRef: { name: "ciconnect-creds", key: "token" },
              },
            },
            { name: "OWNER", value: settings.owner },
            { name: "OWNER_UID", value: String(settings.owner_uid) },
            { name: "CONNECT_GROUP", value: "atlas-af" },
            { name: "CONNECT_GID", value: "5741" },
          ],
          ports: [{ containerPort: 9999 }],
          resources: {
            limits: {
              cpu: String(settings.cpu_limit),
              memory: settings.memory_limit,
              ...(settings.gpu_limit > 0
                ? { "nvidia.com/gpu": String(settings.gpu_limit) }
                : {}),
            },
            requests: {
              cpu: String(settings.cpu_request),
              memory: settings.memory_request,
              ...(settings.gpu_request > 0
                ? { "nvidia.com/gpu": String(settings.gpu_request) }
                : {}),
            },
          },
          volumeMounts: [
            { name: "nfs-home", mountPath: "/home" },
            { name: "ceph-data", mountPath: "/data" },
            { name: "ceph-work", mountPath: "/work" },
            { name: "ceph-cold", mountPath: "/cold" },
            {
              name: "cvmfs",
              mountPath: "/cvmfs",
              mountPropagation: "HostToContainer",
            },
            { name: "shm-volume", mountPath: "/dev/shm" },
          ],
        },
      ],
      volumes: [
        { name: "shm-volume", emptyDir: { medium: "Memory" } },
        {
          name: "nfs-home",
          nfs: { server: "nfs.af.uchicago.edu", path: "/export/home" },
        },
        { name: "ceph-data", hostPath: { path: "/data" } },
        { name: "ceph-work", hostPath: { path: "/work" } },
        { name: "ceph-cold", hostPath: { path: "/cold" } },
        {
          name: "cvmfs",
          persistentVolumeClaim: { claimName: "cvmfs" },
        },
      ],
    },
  };
  await api.createNamespacedPod({ namespace: NAMESPACE, body: pod });

  // --- Service ---
  const service: k8s.V1Service = {
    apiVersion: "v1",
    kind: "Service",
    metadata: {
      name: notebookId,
      namespace: NAMESPACE,
      labels: { "k8s-app": "jupyterlab" },
    },
    spec: {
      selector: { "notebook-id": notebookId },
      ports: [{ port: 80, targetPort: 9999 as unknown as k8s.IntOrString }],
      type: "NodePort",
    },
  };
  try {
    await api.createNamespacedService({ namespace: NAMESPACE, body: service });
  } catch (e: unknown) {
    if ((e as { statusCode?: number }).statusCode === 409) {
      await api.patchNamespacedService({
        name: notebookId,
        namespace: NAMESPACE,
        body: service,
      });
    } else throw e;
  }

  // --- Secret ---
  const secret: k8s.V1Secret = {
    apiVersion: "v1",
    kind: "Secret",
    metadata: {
      name: notebookId,
      namespace: NAMESPACE,
      labels: { "k8s-app": "jupyterlab", owner: settings.owner },
    },
    type: "Opaque",
    data: { token: tokenB64 },
  };
  try {
    await api.createNamespacedSecret({ namespace: NAMESPACE, body: secret });
  } catch (e: unknown) {
    if ((e as { statusCode?: number }).statusCode === 409) {
      await api.patchNamespacedSecret({
        name: notebookId,
        namespace: NAMESPACE,
        body: secret,
      });
    } else throw e;
  }

  // --- Ingress ---
  const ingress: k8s.V1Ingress = {
    apiVersion: "networking.k8s.io/v1",
    kind: "Ingress",
    metadata: {
      name: notebookId,
      namespace: NAMESPACE,
      labels: { "k8s-app": "jupyterlab" },
      annotations: {
        "cert-manager.io/cluster-issuer": "letsencrypt-prod",
        "kubernetes.io/ingress.class": "nginx",
      },
    },
    spec: {
      rules: [
        {
          host: `${notebookId}.${DOMAIN_NAME}`,
          http: {
            paths: [
              {
                path: "/",
                pathType: "Prefix",
                backend: {
                  service: {
                    name: notebookId,
                    port: { number: 80 },
                  },
                },
              },
            ],
          },
        },
      ],
      tls: [
        {
          hosts: [`*.${DOMAIN_NAME}`],
          secretName: "notebook-tls",
        },
      ],
    },
  };
  try {
    await netApi.createNamespacedIngress({ namespace: NAMESPACE, body: ingress });
  } catch (e: unknown) {
    if ((e as { statusCode?: number }).statusCode === 409) {
      await netApi.patchNamespacedIngress({
        name: notebookId,
        namespace: NAMESPACE,
        body: ingress,
      });
    } else throw e;
  }
}

export async function getNotebook(
  name?: string,
  pod?: k8s.V1Pod,
  options: { log?: boolean; url?: boolean } = {}
): Promise<Notebook> {
  const api = getCoreV1Api();
  if (!pod) {
    const result = await api.readNamespacedPod({
      name: name!.toLowerCase(),
      namespace: NAMESPACE,
    });
    pod = result;
  }

  const notebook: Partial<Notebook> = {};
  const meta = pod.metadata!;
  const spec = pod.spec!;
  const status = pod.status!;

  notebook.id = meta.name!;
  notebook.name = meta.labels?.["notebook-name"] ?? meta.name!;
  notebook.namespace = NAMESPACE;
  notebook.owner = meta.labels?.["owner"] ?? "";
  notebook.image = spec.containers?.[0]?.image ?? "";
  notebook.node = spec.nodeName ?? undefined;
  notebook.node_selector = spec.nodeSelector ?? undefined;
  notebook.pod_status = status.phase ?? "Unknown";
  notebook.creation_date = meta.creationTimestamp!.toISOString();

  const expirationDate = getExpirationDate(pod);
  const now = new Date();
  notebook.expiration_date = expirationDate
    ? expirationDate.toISOString()
    : new Date(now.getTime() + 24 * 3600000).toISOString();
  notebook.hours_remaining = expirationDate
    ? Math.max(
        0,
        Math.floor((expirationDate.getTime() - now.getTime()) / 3600000)
      )
    : 0;

  const containerResources = spec.containers?.[0]?.resources;
  notebook.requests = (containerResources?.requests as Record<string, string>) ?? {};
  notebook.limits = (containerResources?.limits as Record<string, string>) ?? {};

  const conditionOrder: Record<string, number> = {
    PodScheduled: 0,
    Initialized: 1,
    PodReadyToStartContainers: 2,
    ContainersReady: 3,
    Ready: 4,
  };
  notebook.conditions = (status.conditions ?? [])
    .map((c) => ({
      type: c.type,
      status: c.status,
      timestamp: c.lastTransitionTime?.toISOString() ?? "",
    }))
    .sort(
      (a, b) =>
        (conditionOrder[a.type] ?? 99) - (conditionOrder[b.type] ?? 99)
    );

  try {
    const eventsResult = await api.listNamespacedEvent({
      namespace: NAMESPACE,
      fieldSelector: `involvedObject.uid=${meta.uid}`,
    });
    notebook.events = eventsResult.items.map((e) => ({
      message: e.message ?? "",
      timestamp: e.lastTimestamp?.toISOString() ?? null,
    }));
  } catch {
    notebook.events = [];
  }

  if (spec.nodeName) {
    try {
      const node = await api.readNode({ name: spec.nodeName });
      const labels = node.metadata?.labels ?? {};
      if (labels["gpu"] === "true") {
        notebook.gpu = {
          product: labels["nvidia.com/gpu.product"] ?? "",
          memory: (labels["nvidia.com/gpu.memory"] ?? "") + "Mi",
        };
      }
    } catch {
      // node not accessible
    }
  }

  let log: string | undefined;
  const isDeleting = meta.deletionTimestamp != null;
  if (!isDeleting) {
    const readyCondition = (status.conditions ?? []).find(
      (c) => c.type === "Ready" && c.status === "True"
    );
    if (readyCondition) {
      try {
        log = await api.readNamespacedPodLog({
          name: meta.name!,
          namespace: NAMESPACE,
        });
        notebook.status = /Jupyter.*is running at/.test(log ?? "")
          ? "Ready"
          : "Starting notebook...";
      } catch {
        notebook.status = "Starting notebook...";
      }
    } else {
      notebook.status = "Pending";
    }
  } else {
    notebook.status = "Removing notebook...";
  }

  if (options.log && log !== undefined) notebook.log = log;
  if (options.url && !isDeleting) {
    try {
      const secretResult = await api.readNamespacedSecret({
        name: meta.name!,
        namespace: NAMESPACE,
      });
      const tokenData = secretResult.data?.["token"];
      if (tokenData) {
        const tokenValue = Buffer.from(tokenData, "base64").toString();
        notebook.url = `https://${meta.name}.${DOMAIN_NAME}?token=${encodeURIComponent(tokenValue)}`;
      }
    } catch {
      // token not available yet
    }
  }

  return notebook as Notebook;
}

export async function getNotebooks(
  owner?: string,
  options: { log?: boolean; url?: boolean } = {}
): Promise<Notebook[]> {
  const api = getCoreV1Api();
  const labelSelector =
    owner == null
      ? "k8s-app=jupyterlab"
      : `k8s-app=jupyterlab,owner=${owner}`;
  const result = await api.listNamespacedPod({
    namespace: NAMESPACE,
    labelSelector,
  });
  const notebooks: Notebook[] = [];
  for (const pod of result.items) {
    try {
      notebooks.push(await getNotebook(undefined, pod, options));
    } catch {
      // skip problematic pods
    }
  }
  return notebooks;
}

export async function listNotebooks(): Promise<string[]> {
  const api = getCoreV1Api();
  const result = await api.listNamespacedPod({
    namespace: NAMESPACE,
    labelSelector: "k8s-app=jupyterlab",
  });
  return result.items.map((p) => p.metadata!.name!);
}

export async function removeNotebook(name: string): Promise<boolean> {
  try {
    const id = name.toLowerCase();
    const api = getCoreV1Api();
    const netApi = getNetworkingV1Api();
    await api.deleteNamespacedPod({ name: id, namespace: NAMESPACE });
    await api.deleteNamespacedService({ name: id, namespace: NAMESPACE });
    await api.deleteNamespacedSecret({ name: id, namespace: NAMESPACE });
    await netApi.deleteNamespacedIngress({ name: id, namespace: NAMESPACE });
    return true;
  } catch {
    return false;
  }
}

export async function notebookNameAvailable(name: string): Promise<boolean> {
  const api = getCoreV1Api();
  const result = await api.listNamespacedPod({
    namespace: NAMESPACE,
    fieldSelector: `metadata.name=${name.toLowerCase()}`,
  });
  return result.items.length === 0;
}

export async function generateNotebookName(
  owner: string
): Promise<string | null> {
  for (let i = 1; i <= 20; i++) {
    const name = `${owner}-notebook-${i}`;
    if (await notebookNameAvailable(name)) return name;
  }
  return null;
}

export function supportedImages(): string[] {
  return [
    "hub.opensciencegrid.org/usatlas/ml-platform:latest",
    "hub.opensciencegrid.org/usatlas/ml-platform:2026.3",
    "hub.opensciencegrid.org/usatlas/analysis-dask-uc:main",
    "hub.opensciencegrid.org/usatlas/analysis-dask-uc:dev",
  ];
}

export async function getGpuAvailability(
  product?: string,
  memory?: number
): Promise<GpuAvailability[]> {
  const api = getCoreV1Api();
  let labelSelector: string;
  if (product) {
    labelSelector = `gpu=true,nvidia.com/gpu.product=${product}`;
  } else if (memory) {
    labelSelector = `gpu=true,nvidia.com/gpu.memory=${memory}`;
  } else {
    labelSelector = "nvidia.com/gpu.product";
  }
  const nodesResult = await api.listNode({ labelSelector });
  const gpus: Record<string, GpuAvailability> = {};

  for (const node of nodesResult.items) {
    const labels = node.metadata?.labels ?? {};
    const prod = labels["nvidia.com/gpu.product"] ?? "";
    const mem = parseInt(labels["nvidia.com/gpu.memory"] ?? "0", 10);
    const count = parseInt(labels["nvidia.com/gpu.count"] ?? "0", 10);

    if (!gpus[prod]) {
      gpus[prod] = {
        product: prod,
        memory: mem,
        count,
        total_requests: 0,
        available: 0,
        cpu_request_max: 0,
        mem_request_max: 0,
      };
    } else {
      gpus[prod].count += count;
    }
    const gpu = gpus[prod];

    // get pods on this node
    const podsResult = await api.listPodForAllNamespaces({
      fieldSelector: `spec.nodeName=${node.metadata!.name},status.phase!=Succeeded,status.phase!=Failed`,
    });
    let memReq = 0;
    let cpuReq = 0;
    let gpuReq = 0;
    for (const pod of podsResult.items) {
      for (const container of pod.spec?.containers ?? []) {
        const reqs = container.resources?.requests ?? {};
        gpu.total_requests += parseInt(
          String(reqs["nvidia.com/gpu"] ?? 0),
          10
        );
        gpuReq += parseInt(String(reqs["nvidia.com/gpu"] ?? 0), 10);
        memReq += parseQuantityBytes(String(reqs["memory"] ?? "0"));
        cpuReq += parseQuantityCores(String(reqs["cpu"] ?? "0"));
      }
    }

    const nodeGpuTotal = parseInt(
      String(node.status?.capacity?.["nvidia.com/gpu"] ?? "0"),
      10
    );
    if (nodeGpuTotal > gpuReq) {
      const nodeMemBytes = parseQuantityBytes(
        String(node.status?.capacity?.["memory"] ?? "0")
      );
      const nodeCpuCores = parseQuantityCores(
        String(node.status?.capacity?.["cpu"] ?? "0")
      );
      const memReqMaxGb = Math.floor(
        (nodeMemBytes - memReq) / (1024 * 1024 * 1024)
      );
      const cpuReqMax = Math.floor(nodeCpuCores - cpuReq);
      if (memReqMaxGb > gpu.mem_request_max) gpu.mem_request_max = memReqMaxGb;
      if (cpuReqMax > gpu.cpu_request_max) gpu.cpu_request_max = cpuReqMax;
    }
    gpu.available = Math.max(gpu.count - gpu.total_requests, 0);
  }
  return Object.values(gpus).sort((a, b) => a.memory - b.memory);
}

function getExpirationDate(pod: k8s.V1Pod): Date | null {
  const label = pod.metadata?.labels?.["time2delete"] ?? "";
  const match = label.match(/^ttl-(\d+)$/);
  if (match) {
    const hours = parseInt(match[1], 10);
    const created = pod.metadata!.creationTimestamp!;
    return new Date(created.getTime() + hours * 3600000);
  }
  return null;
}

function parseQuantityBytes(q: string): number {
  if (!q || q === "0") return 0;
  const units: Record<string, number> = {
    Ki: 1024,
    Mi: 1024 ** 2,
    Gi: 1024 ** 3,
    Ti: 1024 ** 4,
    K: 1000,
    M: 1000 ** 2,
    G: 1000 ** 3,
    T: 1000 ** 4,
  };
  for (const [suffix, mult] of Object.entries(units)) {
    if (q.endsWith(suffix)) {
      return parseFloat(q.slice(0, -suffix.length)) * mult;
    }
  }
  return parseFloat(q);
}

function parseQuantityCores(q: string): number {
  if (!q || q === "0") return 0;
  if (q.endsWith("m")) return parseFloat(q.slice(0, -1)) / 1000;
  return parseFloat(q);
}

export async function getPod(name: string): Promise<k8s.V1Pod | null> {
  try {
    const api = getCoreV1Api();
    return await api.readNamespacedPod({
      name: name.toLowerCase(),
      namespace: NAMESPACE,
    });
  } catch {
    return null;
  }
}
