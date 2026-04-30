import https from "node:https";
import http from "node:http";
import type { UserProfile, Group, UserRole } from "@/types";

const BASE_URL = process.env.CONNECT_API_ENDPOINT!;
const TOKEN = process.env.CONNECT_API_TOKEN!;

// Use node:https (not undici/native-fetch) so TLS options are actually applied.
// When undici is webpack-bundled the Agent comes from a different module instance
// than the global fetch's built-in undici, so dispatcher options are silently
// ignored. node:https.Agent is a true built-in and reliably passes TLS settings.
const _httpsAgent = new https.Agent({
  rejectUnauthorized: false,
});

function apiFetch(url: string, init?: RequestInit): Promise<Response> {
  return new Promise<Response>((resolve, reject) => {
    const parsed = new URL(url);
    const isHttps = parsed.protocol === "https:";
    const body = init?.body != null ? (init.body as string) : undefined;
    const options = {
      hostname: parsed.hostname,
      port: parsed.port || (isHttps ? "443" : "80"),
      path: parsed.pathname + parsed.search,
      method: (init?.method ?? "GET").toUpperCase(),
      headers: (init?.headers ?? {}) as Record<string, string>,
    };
    const onResponse = (res: http.IncomingMessage) => {
      const chunks: Buffer[] = [];
      res.on("data", (c: Buffer) => chunks.push(c));
      res.on("end", () =>
        resolve(
          new Response(Buffer.concat(chunks), {
            status: res.statusCode ?? 200,
            headers: Object.fromEntries(
              Object.entries(res.headers)
                .filter(([, v]) => v !== undefined)
                .map(([k, v]) => [k, Array.isArray(v) ? v.join(", ") : String(v)])
            ),
          })
        )
      );
      res.on("error", reject);
    };
    const req = isHttps
      ? https.request({ ...options, agent: _httpsAgent }, onResponse)
      : http.request(options, onResponse);
    req.on("error", reject);
    req.end(body);
  });
}

export class ConnectApiError extends Error {}

function buildUrl(path: string, extra?: Record<string, string>): string {
  const url = new URL(path, BASE_URL);
  url.searchParams.set("token", TOKEN);
  if (extra) {
    for (const [k, v] of Object.entries(extra)) {
      url.searchParams.set(k, v);
    }
  }
  return url.toString();
}

async function connectFetch(path: string, init?: RequestInit) {
  const url = buildUrl(path);
  const res = await apiFetch(url, { ...init, cache: "no-store" });
  if (!res.ok && res.status !== 404) {
    throw new ConnectApiError(`Connect API error: ${res.status}`);
  }
  const text = await res.text();
  if (!text) return null;
  const data = JSON.parse(text);
  if (data?.kind === "Error") {
    throw new ConnectApiError(data.message ?? "Unknown error");
  }
  return data;
}

function parseDate(raw: string, fmt: string = "calendar"): string {
  if (!raw) return "";
  const d = new Date(raw);
  if (fmt === "calendar") {
    return d.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }
  if (fmt === "iso") return d.toISOString();
  if (fmt === "%m/%d/%Y") {
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    const yyyy = d.getFullYear();
    return `${mm}/${dd}/${yyyy}`;
  }
  return d.toISOString();
}

function resolveRole(
  groupMemberships: { name: string; state: UserRole }[]
): UserRole {
  const membership = groupMemberships.find((g) => g.name === "root.atlas-af");
  return membership ? membership.state : "nonmember";
}

function parseProfileMetadata(
  metadata: Record<string, unknown>,
  dateFormat = "calendar"
): UserProfile {
  const memberships = (metadata.group_memberships as {
    name: string;
    state: UserRole;
  }[]) ?? [];
  memberships.sort((a, b) => a.name.localeCompare(b.name));
  return {
    unix_name: metadata.unix_name as string,
    unix_id: metadata.unix_id as number,
    name: metadata.name as string,
    email: metadata.email as string,
    institution: metadata.institution as string,
    phone: metadata.phone as string,
    public_key: metadata.public_key as string,
    join_date: parseDate(metadata.join_date as string, dateFormat),
    totp_secret: metadata.totp_secret as string | undefined,
    group_memberships: memberships,
    role: resolveRole(memberships),
  };
}

function parseGroupMetadata(
  metadata: Record<string, unknown>,
  roles?: Record<string, UserRole>,
  dateFormat = "calendar"
): Group {
  return {
    name: metadata.name as string,
    display_name: metadata.display_name as string,
    description: metadata.description as string,
    email: metadata.email as string,
    phone: metadata.phone as string,
    purpose: metadata.purpose as string,
    unix_id: metadata.unix_id as number,
    pending: metadata.pending as boolean,
    creation_date: parseDate(metadata.creation_date as string, dateFormat),
    is_removable: isGroupRemovable(metadata.name as string),
    role: roles ? roles[metadata.name as string] : undefined,
  };
}

const NON_REMOVABLE_GROUPS = new Set([
  "root",
  "root.atlas-af",
  "root.atlas-af.staff",
  "root.atlas-af.uchicago",
  "root.atlas-ml",
  "root.atlas-ml.staff",
  "root.iris-hep-ml",
  "root.iris-hep-ml.staff",
  "root.osg",
  "root.osg.login-nodes",
]);

export function isGroupRemovable(groupName: string): boolean {
  return !NON_REMOVABLE_GROUPS.has(groupName);
}

export async function getUsername(globusId: string): Promise<string | null> {
  const data = await connectFetch(
    `/v1alpha1/find_user?globus_id=${encodeURIComponent(globusId)}`
  );
  if (data?.kind === "User") return data.metadata.unix_name as string;
  return null;
}

export async function getUsernames(
  groupName: string,
  roles: UserRole[] = ["admin", "active", "pending"]
): Promise<string[]> {
  const data = await connectFetch(`/v1alpha1/groups/${groupName}/members`);
  if (!data?.memberships) return [];
  return (
    data.memberships as { user_name: string; state: UserRole }[]
  )
    .filter((m) => roles.includes(m.state))
    .map((m) => m.user_name);
}

export async function getConnectUserProfile(
  username: string,
  dateFormat = "calendar"
): Promise<UserProfile | null> {
  const data = await connectFetch(`/v1alpha1/users/${username}`);
  if (data?.kind === "User") {
    return parseProfileMetadata(data.metadata, dateFormat);
  }
  return null;
}

export async function getUserProfiles(
  groupName: string,
  roles: UserRole[] = ["admin", "active", "pending"],
  dateFormat = "calendar"
): Promise<UserProfile[]> {
  const usernames = await getUsernames(groupName, roles);
  if (usernames.length === 0) return [];
  const requestData: Record<string, { method: string }> = {};
  for (const u of usernames) {
    requestData[`/v1alpha1/users/${u}?token=${TOKEN}`] = { method: "GET" };
  }
  const url = buildUrl("/v1alpha1/multiplex");
  const res = await apiFetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestData),
    cache: "no-store",
  });
  const data = await res.json();
  if (data?.kind === "Error") throw new ConnectApiError(data.message);
  const profiles: UserProfile[] = [];
  for (const value of Object.values(
    data as Record<string, { body: string }>
  )) {
    try {
      const body = JSON.parse(value.body);
      profiles.push(parseProfileMetadata(body.metadata, dateFormat));
    } catch {
      // skip malformed entries
    }
  }
  return profiles;
}

export async function createUserProfile(settings: {
  globus_id: string;
  unix_name: string;
  name: string;
  institution: string;
  email: string;
  phone: string;
  public_key: string;
}): Promise<void> {
  const body = {
    apiVersion: "v1alpha1",
    metadata: {
      globusID: settings.globus_id,
      unix_name: settings.unix_name,
      name: settings.name,
      institution: settings.institution,
      email: settings.email,
      phone: settings.phone,
      public_key: settings.public_key,
      superuser: false,
      service_account: false,
      create_totp_secret: true,
    },
  };
  const url = buildUrl("/v1alpha1/users");
  const res = await apiFetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  const data = await res.json();
  if (data?.kind === "Error") throw new ConnectApiError(data.message);
}

export async function updateUserProfile(
  username: string,
  settings: Partial<{
    name: string;
    institution: string;
    email: string;
    phone: string;
    public_key: string;
    create_totp_secret: boolean;
  }>
): Promise<void> {
  const body = { apiVersion: "v1alpha1", kind: "User", metadata: settings };
  const url = buildUrl(`/v1alpha1/users/${username}`);
  const res = await apiFetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  const data = await res.json();
  if (data?.kind === "Error") throw new ConnectApiError(data.message);
}

export async function getUserGroups(
  username: string,
  pattern?: string,
  dateFormat = "calendar"
): Promise<Group[]> {
  const profile = await getConnectUserProfile(username);
  if (!profile) return [];
  const roles: Record<string, UserRole> = {};
  for (const m of profile.group_memberships) {
    roles[m.name] = m.state;
  }
  const requestData: Record<string, { method: string }> = {};
  for (const groupName of Object.keys(roles)) {
    requestData[`/v1alpha1/groups/${groupName}?token=${TOKEN}`] = {
      method: "GET",
    };
  }
  if (Object.keys(requestData).length === 0) return [];
  const url = buildUrl("/v1alpha1/multiplex");
  const res = await apiFetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestData),
    cache: "no-store",
  });
  const data = await res.json();
  if (data?.kind === "Error") throw new ConnectApiError(data.message);
  const groups: Group[] = [];
  for (const value of Object.values(
    data as Record<string, { status: number; body: string }>
  )) {
    if (value.status !== 200) continue;
    try {
      const body = JSON.parse(value.body);
      const group = parseGroupMetadata(body.metadata, roles, dateFormat);
      if (pattern && !group.name.startsWith(pattern)) continue;
      groups.push(group);
    } catch {
      // skip
    }
  }
  groups.sort((a, b) => a.name.localeCompare(b.name));
  return groups;
}

export async function removeUserFromGroup(
  username: string,
  groupName: string
): Promise<void> {
  const url = buildUrl(
    `/v1alpha1/groups/${groupName}/members/${username}`
  );
  const res = await apiFetch(url, { method: "DELETE", cache: "no-store" });
  const data = await res.json();
  if (data?.kind === "Error") throw new ConnectApiError(data.message);
}

export async function getUserRoles(
  username: string
): Promise<Record<string, UserRole>> {
  const profile = await getConnectUserProfile(username);
  if (!profile) return {};
  return Object.fromEntries(
    profile.group_memberships.map((m) => [m.name, m.state])
  );
}

export async function updateUserRole(
  username: string,
  groupName: string,
  role: UserRole
): Promise<void> {
  const body = {
    apiVersion: "v1alpha1",
    group_membership: { state: role },
  };
  const url = buildUrl(`/v1alpha1/groups/${groupName}/members/${username}`);
  const res = await apiFetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  const data = await res.json();
  if (data?.kind === "Error") throw new ConnectApiError(data.message);
}

export async function getGroupInfo(
  groupName: string,
  dateFormat = "calendar"
): Promise<Group | null> {
  const data = await connectFetch(`/v1alpha1/groups/${groupName}`);
  if (data?.kind === "Group") {
    return parseGroupMetadata(data.metadata, undefined, dateFormat);
  }
  return null;
}

export async function updateGroupInfo(
  groupName: string,
  settings: Partial<{
    display_name: string;
    email: string;
    phone: string;
    description: string;
  }>
): Promise<void> {
  const body = { apiVersion: "v1alpha1", metadata: settings };
  const url = buildUrl(`/v1alpha1/groups/${groupName}`);
  const res = await apiFetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  const data = await res.json();
  if (data?.kind === "Error") throw new ConnectApiError(data.message);
}

export async function removeGroup(groupName: string): Promise<boolean> {
  if (!isGroupRemovable(groupName)) return false;
  const url = buildUrl(`/v1alpha1/groups/${groupName}`);
  const res = await apiFetch(url, { method: "DELETE", cache: "no-store" });
  const data = await res.json();
  if (data?.kind === "Error") throw new ConnectApiError(data.message);
  return true;
}

export async function getSubgroups(
  groupName: string
): Promise<Group[]> {
  const data = await connectFetch(`/v1alpha1/groups/${groupName}/subgroups`);
  return (data?.groups as Group[]) ?? [];
}

export async function createSubgroup(
  groupName: string,
  settings: {
    name: string;
    display_name: string;
    email: string;
    phone: string;
    description: string;
    purpose: string;
  }
): Promise<void> {
  const body = { apiVersion: "v1alpha1", metadata: settings };
  const url = buildUrl(
    `/v1alpha1/groups/${groupName}/subgroup_requests/${settings.name}`
  );
  const res = await apiFetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  const data = await res.json();
  if (data?.kind === "Error") throw new ConnectApiError(data.message);
}
