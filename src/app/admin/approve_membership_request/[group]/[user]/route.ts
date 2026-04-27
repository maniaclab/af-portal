import { NextRequest, NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/guards";
import { updateUserRole, getConnectUserProfile } from "@/lib/connect/client";
import { sendStaffEmail } from "@/lib/email/mailgun";
import { emailQueue } from "@/lib/jobs/queue";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ group: string; user: string }> }
) {
  const { group, user } = await params;
  const { session } = await requireAdmin();
  const approver = session.unix_name!;

  await updateUserRole(user, group, "active");

  emailQueue.add(async () => {
    const profile = await getConnectUserProfile(user);
    const body = `
User ${approver} approved a request from ${user} to join group ${group}.

Unix name: ${profile?.unix_name ?? user}
Full name: ${profile?.name ?? ""}
Email: ${profile?.email ?? ""}
Institution: ${profile?.institution ?? ""}
`;
    await sendStaffEmail("Account approval", body);
  });

  return NextResponse.json({ success: true });
}
