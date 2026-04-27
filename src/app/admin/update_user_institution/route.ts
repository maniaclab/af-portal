import { NextRequest, NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/guards";
import { updateUserProfile } from "@/lib/connect/client";

export async function POST(request: NextRequest) {
  await requireAdmin();
  const formData = await request.formData();
  const username = formData.get("username") as string;
  const institution = formData.get("institution") as string;
  await updateUserProfile(username, { institution });
  return NextResponse.json({ success: true });
}
