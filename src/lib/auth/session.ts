import { getIronSession, SessionOptions } from "iron-session";
import { cookies } from "next/headers";
import type { FlashMessage, UserRole } from "@/types";

export interface PortalSession {
  is_authenticated: boolean;
  tokens: Record<string, { access_token: string; refresh_token?: string }>;
  name: string;
  email: string;
  institution: string;
  globus_id: string;
  last_authentication: number;
  unix_name?: string;
  unix_id?: number;
  role?: UserRole;
  flash?: FlashMessage;
}

export const sessionOptions: SessionOptions = {
  password: process.env.SESSION_SECRET!,
  cookieName: "af-portal-session",
  cookieOptions: {
    secure: process.env.NODE_ENV === "production",
    httpOnly: true,
    sameSite: "lax",
  },
};

export async function getSession() {
  return getIronSession<PortalSession>(await cookies(), sessionOptions);
}
