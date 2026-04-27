"use server";
import { redirect } from "next/navigation";
import { requireLogin } from "@/lib/auth/guards";
import {
  createUserProfile,
  updateUserRole,
  ConnectApiError,
} from "@/lib/connect/client";

export async function createProfileAction(
  _prev: string | null,
  formData: FormData
): Promise<string | null> {
  const session = await requireLogin();

  const profile = {
    globus_id: session.globus_id,
    unix_name: (formData.get("unix_name") as string).trim(),
    name: (formData.get("name") as string).trim(),
    email: (formData.get("email") as string).trim(),
    phone: (formData.get("phone") as string).trim(),
    institution: (formData.get("institution") as string).trim(),
    public_key: ((formData.get("public_key") as string) ?? "").trim(),
  };

  try {
    await createUserProfile(profile);
    await updateUserRole(profile.unix_name, "root.atlas-af", "pending");
    session.unix_name = profile.unix_name;
    session.role = "pending";
    session.flash = {
      message: "Successfully created profile",
      category: "success",
    };
    await session.save();
  } catch (err) {
    if (err instanceof ConnectApiError) return err.message;
    return "Failed to create profile";
  }

  redirect("/profile");
}
