import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/guards";
import { listNotebooks } from "@/lib/kubernetes/notebooks";

export async function GET() {
  await requireAdmin();
  const notebooks = await listNotebooks();
  return NextResponse.json({ notebooks });
}
