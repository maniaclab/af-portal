import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth/session";
import { updateUserRole, ConnectApiError } from "@/lib/connect/client";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ unix_name: string }> }
) {
  const { unix_name } = await params;
  const session = await getSession();
  if (!session.is_authenticated) {
    return NextResponse.redirect(new URL("/auth/login", _req.url));
  }
  try {
    await updateUserRole(unix_name, "root.atlas-af", "pending");
    session.flash = {
      message: "Requested membership in the ATLAS Analysis Facility group",
      category: "success",
    };
  } catch (err) {
    session.flash = {
      message:
        err instanceof ConnectApiError ? err.message : "Request failed",
      category: "warning",
    };
  }
  await session.save();
  return NextResponse.redirect(new URL("/profile", _req.url));
}
