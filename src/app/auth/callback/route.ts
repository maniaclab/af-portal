import { NextRequest, NextResponse } from "next/server";
import { exchangeCode, decodeIdToken } from "@/lib/auth/globus";
import { getSession } from "@/lib/auth/session";
import { getUsername, getConnectUserProfile } from "@/lib/connect/client";

function getBaseUrl(request: NextRequest): string {
  const proto = request.headers.get("x-forwarded-proto") ?? "https";
  const host =
    request.headers.get("x-forwarded-host") ??
    (process.env.DOMAIN_NAME ?? request.headers.get("host") ?? "localhost:3000");
  return `${proto}://${host}`;
}

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state");

  if (!code) {
    return NextResponse.redirect(new URL("/", getBaseUrl(request)));
  }

  const tokens = await exchangeCode(code);
  const idToken = decodeIdToken(tokens.id_token);

  const session = await getSession();
  session.is_authenticated = true;
  session.tokens = tokens.by_resource_server;
  session.name = idToken.name ?? "";
  session.email = idToken.email ?? "";
  session.institution = idToken.organization ?? "";
  session.globus_id = idToken.sub;
  session.last_authentication = idToken.last_authentication ?? -1;

  const username = await getUsername(idToken.sub);
  if (username) {
    const profile = await getConnectUserProfile(username);
    if (profile) {
      session.unix_name = profile.unix_name;
      session.unix_id = profile.unix_id;
      session.role = profile.role;
    } else {
      session.role = "nonmember";
    }
    await session.save();
    const base = getBaseUrl(request);
    const target = state && state.startsWith("/") ? state : "/";
    return NextResponse.redirect(new URL(target, base));
  } else {
    await session.save();
    return NextResponse.redirect(new URL("/profile/create", getBaseUrl(request)));
  }
}
