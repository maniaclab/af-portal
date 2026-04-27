import { NextRequest, NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/guards";
import { getUserProfiles } from "@/lib/connect/client";

export async function GET(
  _request: NextRequest,
  { params: _ }: { params: Promise<{ name: string }> }
) {
  await requireAdmin();
  const users = await getUserProfiles("root");
  const potential_members = users.filter(
    (u) => u.role === "nonmember" || u.role === "pending"
  );
  return NextResponse.json({ potential_members });
}
