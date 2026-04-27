import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth/session";
import { revokeToken } from "@/lib/auth/globus";

export async function GET(request: NextRequest) {
  const session = await getSession();
  if (session.is_authenticated && session.tokens) {
    await Promise.allSettled(
      Object.values(session.tokens).map((t) => revokeToken(t.access_token))
    );
  }
  session.destroy();
  return NextResponse.redirect(new URL("/", request.url));
}
