import { NextRequest } from "next/server";
import { redirect } from "next/navigation";
import { requireAdmin } from "@/lib/auth/guards";
import { removeGroup } from "@/lib/connect/client";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  const { name } = await params;
  const { session } = await requireAdmin();
  await removeGroup(name);
  session.flash = { message: `Removed group ${name}`, category: "success" };
  await session.save();
  redirect("/admin/groups/root.atlas-af");
}
