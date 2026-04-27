import { NextResponse } from "next/server";
import { getSession } from "@/lib/auth/session";
import { getUserGroups } from "@/lib/connect/client";

export async function GET() {
  const session = await getSession();
  if (!session.is_authenticated || !session.unix_name) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const groups = await getUserGroups(session.unix_name, "root.atlas-af");
  return NextResponse.json({ groups });
}
