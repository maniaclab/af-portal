import { decodeJwt } from "jose";

const CLIENT_ID = process.env.GLOBUS_CLIENT_ID!;
const CLIENT_SECRET = process.env.GLOBUS_CLIENT_SECRET!;
const REDIRECT_URI = process.env.GLOBUS_REDIRECT_URI!;

const AUTH_BASE = "https://auth.globus.org/v2/oauth2";

export function getAuthorizeUrl(state?: string): string {
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    scope: "openid profile email",
    response_type: "code",
    access_type: "offline",
  });
  if (state) params.set("state", state);
  return `${AUTH_BASE}/authorize?${params}`;
}

export interface GlobusTokens {
  access_token: string;
  refresh_token?: string;
  id_token: string;
  token_type: string;
  expires_in: number;
  resource_server: string;
  by_resource_server: Record<
    string,
    { access_token: string; refresh_token?: string }
  >;
}

export async function exchangeCode(code: string): Promise<GlobusTokens> {
  const credentials = Buffer.from(`${CLIENT_ID}:${CLIENT_SECRET}`).toString(
    "base64"
  );
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: REDIRECT_URI,
  });
  const res = await fetch(`${AUTH_BASE}/token`, {
    method: "POST",
    headers: {
      Authorization: `Basic ${credentials}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Globus token exchange failed: ${text}`);
  }
  const data = await res.json();
  const by_resource_server: Record<
    string,
    { access_token: string; refresh_token?: string }
  > = {};
  by_resource_server[data.resource_server ?? "auth.globus.org"] = {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
  };
  if (Array.isArray(data.other_tokens)) {
    for (const t of data.other_tokens) {
      by_resource_server[t.resource_server] = {
        access_token: t.access_token,
        refresh_token: t.refresh_token,
      };
    }
  }
  return { ...data, by_resource_server };
}

export interface GlobusIdToken {
  sub: string;
  name?: string;
  email?: string;
  organization?: string;
  last_authentication?: number;
}

export function decodeIdToken(idToken: string): GlobusIdToken {
  return decodeJwt(idToken) as unknown as GlobusIdToken;
}

export async function revokeToken(token: string): Promise<void> {
  const credentials = Buffer.from(`${CLIENT_ID}:${CLIENT_SECRET}`).toString(
    "base64"
  );
  await fetch(`${AUTH_BASE}/revoke_token`, {
    method: "POST",
    headers: {
      Authorization: `Basic ${credentials}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({ token }),
  });
}
