import "server-only";
import { cookies } from "next/headers";
import { randomBytes } from "node:crypto";
export const SESSION_COOKIE = "kontur_session";
export const STATE_COOKIE = "kontur_oauth_state";
export type Session = {
  user: { id: string; name: string; avatar: string | null };
  accessToken: string;
  expiresAt: number;
};
const globalSessions = globalThis as typeof globalThis & {
  konturSessions?: Map<string, Session>;
};
const sessions = (globalSessions.konturSessions ??= new Map());
export function authConfig() {
  const id = process.env.DISCORD_CLIENT_ID || "";
  const secret = process.env.DISCORD_CLIENT_SECRET || "";
  const sessionSecret = process.env.SESSION_SECRET || "";
  const configuredBase = process.env.SITE_URL || "http://127.0.0.1:3000";
  let base = "http://127.0.0.1:3000";
  let validBase = false;
  try {
    const url = new URL(configuredBase);
    validBase =
      !url.username &&
      !url.password &&
      !url.search &&
      !url.hash &&
      url.pathname === "/" &&
      (url.protocol === "https:" ||
        (process.env.NODE_ENV !== "production" &&
          url.protocol === "http:" &&
          ["localhost", "127.0.0.1"].includes(url.hostname)));
    if (validBase) base = url.origin;
  } catch {}
  return {
    id,
    secret,
    sessionSecret,
    base,
    ready:
      /^\d{17,20}$/.test(id) &&
      !!secret &&
      sessionSecret.length >= 32 &&
      validBase,
  };
}
export const cookieOptions = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax" as const,
  path: "/",
};
export function saveSession(session: Session): string {
  for (const [key, value] of sessions)
    if (value.expiresAt <= Date.now()) sessions.delete(key);
  if (sessions.size >= 1000) sessions.delete(sessions.keys().next().value!);
  const id = randomBytes(32).toString("base64url");
  sessions.set(id, session);
  return id;
}
export async function getSession(): Promise<Session | null> {
  const id = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!id) return null;
  const session = sessions.get(id);
  if (!session || session.expiresAt <= Date.now()) {
    sessions.delete(id);
    return null;
  }
  return session;
}
export async function deleteSession() {
  const id = (await cookies()).get(SESSION_COOKIE)?.value;
  if (id) sessions.delete(id);
}
