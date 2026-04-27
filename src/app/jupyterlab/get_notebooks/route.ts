import { NextResponse } from "next/server";
import { getSession } from "@/lib/auth/session";
import { getNotebooks } from "@/lib/kubernetes/notebooks";

export async function GET() {
  const session = await getSession();
  if (!session.is_authenticated || !session.unix_name) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const notebooks = await getNotebooks(session.unix_name, { url: true });
  return NextResponse.json({ notebooks });
}
