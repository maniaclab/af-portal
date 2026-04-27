import { redirect } from "next/navigation";
import { getSession } from "./session";
import type { UserProfile } from "@/types";
import { getConnectUserProfile } from "@/lib/connect/client";

export async function requireLogin() {
  const session = await getSession();
  if (!session.is_authenticated) redirect("/auth/login");
  return session;
}

export async function requireMember(): Promise<{
  session: Awaited<ReturnType<typeof getSession>>;
  profile: UserProfile;
}> {
  const session = await requireLogin();
  if (!session.unix_name) redirect("/profile/create");
  const profile = await getConnectUserProfile(session.unix_name);
  if (!profile) redirect("/profile/create");
  if (profile.role !== "admin" && profile.role !== "active") {
    redirect("/profile/request_membership/" + session.unix_name);
  }
  return { session, profile };
}

export async function requireAdmin(): Promise<{
  session: Awaited<ReturnType<typeof getSession>>;
  profile: UserProfile;
}> {
  const session = await requireLogin();
  if (!session.unix_name) redirect("/profile/create");
  const profile = await getConnectUserProfile(session.unix_name);
  if (!profile || profile.role !== "admin") redirect("/404");
  return { session, profile };
}
