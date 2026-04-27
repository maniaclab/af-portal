import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/guards";
import { getUserProfiles } from "@/lib/connect/client";

export async function GET() {
  await requireAdmin();
  const profiles = await getUserProfiles("root.atlas-af");
  return NextResponse.json(
    profiles.map((u) => ({
      unix_name: u.unix_name,
      name: u.name,
      email: u.email,
      join_date: u.join_date,
      institution: u.institution,
    }))
  );
}
