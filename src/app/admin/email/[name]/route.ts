import { NextRequest, NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/guards";
import { getUserProfiles } from "@/lib/connect/client";
import { sendEmail } from "@/lib/email/mailgun";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  const { name } = await params;
  await requireAdmin();
  const formData = await request.formData();
  const subject = formData.get("subject") as string;
  const body = formData.get("body") as string;

  const sender = "noreply@af.uchicago.edu";
  const profiles = await getUserProfiles(name);
  const recipients = profiles.map((p) => p.email).filter(Boolean);

  const ok = await sendEmail(sender, recipients, subject, body);
  if (ok) {
    return NextResponse.json({ success: true, message: `Sent email to group ${name}` });
  }
  return NextResponse.json({ success: false, message: `Unable to send email to group ${name}` });
}
