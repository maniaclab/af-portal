import { NextRequest, NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/guards";
import { getSubgroups } from "@/lib/connect/client";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  const { name } = await params;
  await requireAdmin();
  const subgroups = await getSubgroups(name);
  return NextResponse.json({ subgroups });
}
