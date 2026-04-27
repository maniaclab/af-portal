const MAILGUN_API_TOKEN = process.env.MAILGUN_API_TOKEN ?? "";
const MAILGUN_DOMAIN = "api.ci-connect.net";

export async function sendEmail(
  sender: string,
  recipients: string[],
  subject: string,
  body: string
): Promise<boolean> {
  const form = new URLSearchParams();
  form.set("from", `<${sender}>`);
  form.set("to", sender);
  form.set("bcc", recipients.join(","));
  form.set("subject", subject);
  form.set("text", body);

  const resp = await fetch(
    `https://api.mailgun.net/v3/${MAILGUN_DOMAIN}/messages`,
    {
      method: "POST",
      headers: {
        Authorization: `Basic ${Buffer.from(`api:${MAILGUN_API_TOKEN}`).toString("base64")}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: form.toString(),
    }
  );
  return resp.ok;
}

export async function sendStaffEmail(subject: string, body: string): Promise<boolean> {
  const sender = "noreply@af.uchicago.edu";
  const recipients = ["atlas-us-chicago-tier3-admins@lists.uchicago.edu"];
  return sendEmail(sender, recipients, subject, body);
}
