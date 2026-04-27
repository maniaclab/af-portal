import { redirect } from "next/navigation";
import { requireLogin } from "@/lib/auth/guards";
import { getConnectUserProfile } from "@/lib/connect/client";
import EditProfileForm from "./EditProfileForm";

export const metadata = { title: "Analysis Facility - Edit Profile" };

export default async function EditProfilePage() {
  const session = await requireLogin();
  if (!session.unix_name) redirect("/profile/create");
  const profile = await getConnectUserProfile(session.unix_name);
  if (!profile) redirect("/profile/create");
  return <EditProfileForm profile={profile} />;
}
