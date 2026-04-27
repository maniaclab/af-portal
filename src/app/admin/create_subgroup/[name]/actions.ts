"use server";

import { redirect } from "next/navigation";
import { requireAdmin } from "@/lib/auth/guards";
import { createSubgroup } from "@/lib/connect/client";
export async function createSubgroupAction(
  parentName: string,
  formData: FormData
): Promise<void> {
  const { session } = await requireAdmin();
  const name = formData.get("short-name") as string;

  await createSubgroup(parentName, {
    name,
    display_name: formData.get("display-name") as string,
    purpose: (formData.get("purpose") as string) ?? "High Energy Physics",
    email: formData.get("email") as string,
    phone: formData.get("phone") as string,
    description: formData.get("description") as string,
  });
  session.flash = { message: `Created subgroup ${name}`, category: "success" };
  await session.save();
  redirect(`/admin/groups/${parentName}`);
}
