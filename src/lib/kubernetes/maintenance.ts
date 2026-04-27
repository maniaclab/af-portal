import { getCoreV1Api } from "./client";
import { removeNotebook } from "./notebooks";

const NAMESPACE = process.env.NAMESPACE ?? "af";

let maintenanceStarted = false;

export function startNotebookMaintenance(): void {
  if (maintenanceStarted) return;
  maintenanceStarted = true;

  const runCycle = async () => {
    try {
      const api = getCoreV1Api();
      const result = await api.listNamespacedPod({
        namespace: NAMESPACE,
        labelSelector: "k8s-app=jupyterlab",
      });
      const now = new Date();
      for (const pod of result.items) {
        const label = pod.metadata?.labels?.["time2delete"] ?? "";
        const match = label.match(/^ttl-(\d+)$/);
        if (match) {
          const hours = parseInt(match[1], 10);
          const created = pod.metadata?.creationTimestamp;
          if (created) {
            const expiration = new Date(
              created.getTime() + hours * 3600 * 1000
            );
            if (expiration < now) {
              console.log(
                `[maintenance] Removing expired notebook: ${pod.metadata?.name}`
              );
              await removeNotebook(pod.metadata!.name!);
            }
          }
        }
      }
    } catch (err) {
      console.error("[maintenance] Error in notebook maintenance cycle:", err);
    }
    setTimeout(runCycle, 30 * 60 * 1000); // 30 minutes
  };

  setTimeout(runCycle, 30 * 60 * 1000);
  console.log("[maintenance] Notebook maintenance scheduled");
}
