import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth/session";
import { getPod, removeNotebook } from "@/lib/kubernetes/notebooks";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ notebook: string }> }
) {
  const { notebook } = await params;
  const session = await getSession();
  if (!session.is_authenticated || !session.unix_name) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const pod = await getPod(notebook);
  if (pod && pod.metadata?.labels?.["owner"] === session.unix_name) {
    const success = await removeNotebook(notebook);
    if (success) {
      return NextResponse.json({
        success: true,
        message: `Notebook ${notebook} was deleted.`,
      });
    }
  }
  return NextResponse.json({
    success: false,
    message: `Unable to delete notebook ${notebook}`,
  });
}
