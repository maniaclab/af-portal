export function sanitizeK8sPodName(name: string, maxLength = 63): string {
  let n = name.toLowerCase();
  n = n.replace(/[^a-z0-9-]/g, "-");
  n = n.replace(/^-+|-+$/g, "");
  n = n.slice(0, maxLength).replace(/-+$/, "");
  return n || "default-pod";
}
