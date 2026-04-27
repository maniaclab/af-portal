"use server";

import { redirect } from "next/navigation";
import { requireAdmin } from "@/lib/auth/guards";
import { updateGroupInfo } from "@/lib/connect/client";

export async function editGroupAction(
  groupName: string,
  formData: FormData
): Promise<void> {
  const { session } = await requireAdmin();

  try {
    await updateGroupInfo(groupName, {
      display_name: (formData.get("display-name") as string).trim(),
      email: (formData.get("email") as string).trim(),
      phone: (formData.get("phone") as string).trim(),
      description: (formData.get("description") as string).trim(),
    });
    session.flash = { message: `Updated group ${groupName} successfully`, category: "success" };
    await session.save();
  } catch {
    session.flash = { message: `Unable to update group ${groupName}`, category: "warning" };
    await session.save();
    redirect(`/admin/edit_group/${groupName}`);
  }
  redirect(`/admin/groups/${groupName}`);
}
