import { NextRequest, NextResponse } from "next/server";
import { getAuthorizeUrl } from "@/lib/auth/globus";

export async function GET(request: NextRequest) {
  const next = request.nextUrl.searchParams.get("next");
  const url = getAuthorizeUrl(next ?? undefined);
  return NextResponse.redirect(url);
}
