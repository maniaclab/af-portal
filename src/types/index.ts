export type UserRole = "admin" | "active" | "pending" | "nonmember";

export interface GroupMembership {
  name: string;
  state: UserRole;
}

export interface UserProfile {
  unix_name: string;
  unix_id: number;
  globus_id?: string;
  name: string;
  email: string;
  phone: string;
  institution: string;
  public_key: string;
  join_date: string;
  totp_secret?: string;
  group_memberships: GroupMembership[];
  role: UserRole;
}

export interface Group {
  name: string;
  display_name: string;
  description: string;
  email: string;
  phone: string;
  purpose: string;
  unix_id: number;
  pending: boolean;
  creation_date: string;
  is_removable?: boolean;
  role?: UserRole;
}

export interface PodCondition {
  type: string;
  status: string;
  timestamp: string;
}

export interface PodEvent {
  message: string;
  timestamp: string | null;
}

export interface NotebookResources {
  memory?: string;
  cpu?: string;
  "nvidia.com/gpu"?: string;
}

export interface Notebook {
  id: string;
  name: string;
  namespace: string;
  owner: string;
  image: string;
  node?: string;
  node_selector?: Record<string, string>;
  pod_status: string;
  creation_date: string;
  expiration_date: string;
  hours_remaining: number;
  requests: NotebookResources;
  limits: NotebookResources;
  conditions: PodCondition[];
  events: PodEvent[];
  status: "Ready" | "Pending" | "Starting notebook..." | "Removing notebook...";
  gpu?: { product: string; memory: string };
  url?: string;
  log?: string;
}

export interface GpuAvailability {
  product: string;
  memory: number;
  count: number;
  available: number;
  total_requests: number;
  cpu_request_max: number;
  mem_request_max: number;
}

export interface DeployNotebookSettings {
  notebook_name: string;
  notebook_id: string;
  image: string;
  owner: string;
  owner_uid: number;
  globus_id: string;
  cpu_request: number;
  cpu_limit: number;
  memory_request: string;
  memory_limit: string;
  gpu_request: number;
  gpu_limit: number;
  gpu_product: string;
  hours_remaining: number;
}

export interface FlashMessage {
  message: string;
  category: "success" | "warning" | "danger" | "info";
}
