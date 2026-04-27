"use server";
import { redirect } from "next/navigation";
import { requireLogin } from "@/lib/auth/guards";
import { updateUserProfile, ConnectApiError } from "@/lib/connect/client";

export async function editProfileAction(
  _prev: string | null,
  formData: FormData
): Promise<string | null> {
  const session = await requireLogin();
  if (!session.unix_name) redirect("/profile/create");

  const settings: Record<string, string | boolean> = {
    name: (formData.get("name") as string).trim(),
    email: (formData.get("email") as string).trim(),
    phone: (formData.get("phone") as string).trim(),
    institution: (formData.get("institution") as string).trim(),
    public_key: ((formData.get("public_key") as string) ?? "").trim(),
  };
  if (formData.get("totpsecret")) {
    settings.create_totp_secret = true;
  }

  try {
    await updateUserProfile(session.unix_name, settings);
    session.flash = {
      message: "Successfully updated profile",
      category: "success",
    };
    await session.save();
  } catch (err) {
    if (err instanceof ConnectApiError) return err.message;
    return "Failed to update profile";
  }

  redirect("/profile");
}
