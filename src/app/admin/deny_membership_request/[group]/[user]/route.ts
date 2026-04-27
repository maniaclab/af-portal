import { NextRequest, NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/guards";
import { removeUserFromGroup } from "@/lib/connect/client";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ group: string; user: string }> }
) {
  const { group, user } = await params;
  await requireAdmin();
  await removeUserFromGroup(user, group);
  return NextResponse.json({ success: true });
}
