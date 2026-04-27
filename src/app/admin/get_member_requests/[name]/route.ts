import { NextRequest, NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/guards";
import { getUserProfiles } from "@/lib/connect/client";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  const { name } = await params;
  await requireAdmin();
  const profiles = await getUserProfiles(name);
  const member_requests = profiles.filter((p) => p.role === "pending");
  return NextResponse.json({ member_requests });
}
