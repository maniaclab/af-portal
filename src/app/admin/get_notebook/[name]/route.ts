import { NextRequest, NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/guards";
import { getNotebook } from "@/lib/kubernetes/notebooks";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  const { name } = await params;
  await requireAdmin();
  const notebook = await getNotebook(name, undefined, { log: true });
  if (!notebook) {
    return NextResponse.json({ error: "Notebook not found" }, { status: 404 });
  }
  return NextResponse.json({ notebook });
}
