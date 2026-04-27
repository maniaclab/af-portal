export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { startNotebookMaintenance } = await import(
      "./lib/kubernetes/maintenance"
    );
    startNotebookMaintenance();
  }
}
