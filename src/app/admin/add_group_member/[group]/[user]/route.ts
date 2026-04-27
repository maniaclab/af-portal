import { NextRequest, NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/guards";
import { updateUserRole } from "@/lib/connect/client";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ group: string; user: string }> }
) {
  const { group, user } = await params;
  await requireAdmin();
  await updateUserRole(user, group, "active");
  return NextResponse.json({ success: true });
}
