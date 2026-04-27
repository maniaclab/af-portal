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
  const members = profiles.filter((p) => p.role === "active" || p.role === "admin");
  return NextResponse.json({ members });
}
