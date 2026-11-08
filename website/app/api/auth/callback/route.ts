import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import {
  authConfig,
  cookieOptions,
  saveSession,
  SESSION_COOKIE,
  STATE_COOKIE,
} from "@/lib/auth";
import { validId, verifyState } from "@/lib/security";
export async function GET(request: NextRequest) {
  const config = authConfig();
  function failure(reason: string) {
    const reply = NextResponse.redirect(
      new URL(`/dashboard?error=${reason}`, config.base),
    );
    reply.cookies.set(STATE_COOKIE, "", { ...cookieOptions, maxAge: 0 });
    return reply;
  }
  if (!config.ready) return failure("configuration");
  const state = request.nextUrl.searchParams.get("state") || "";
  const expected = (await cookies()).get(STATE_COOKIE)?.value || "";
  if (!verifyState(state, expected, config.sessionSecret))
    return failure("state");
  if (request.nextUrl.searchParams.get("error")) return failure("cancelled");
  const code = request.nextUrl.searchParams.get("code");
  if (
    !code ||
    (request.nextUrl.searchParams.has("iss") &&
      request.nextUrl.searchParams.get("iss") !== "https://discord.com")
  )
    return failure("oauth");
  try {
    const tokenResponse = await fetch(
      "https://discord.com/api/v10/oauth2/token",
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          client_id: config.id,
          client_secret: config.secret,
          grant_type: "authorization_code",
          code,
          redirect_uri: `${config.base}/api/auth/callback`,
        }),
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
      },
    );
    if (!tokenResponse.ok) return failure("oauth");
    const token = await tokenResponse.json();
    if (
      typeof token.access_token !== "string" ||
      !Number.isFinite(token.expires_in) ||
      token.expires_in <= 0
    )
      return failure("oauth");
    const userResponse = await fetch("https://discord.com/api/v10/users/@me", {
      headers: { Authorization: `Bearer ${token.access_token}` },
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
    if (!userResponse.ok) return failure("oauth");
    const user = await userResponse.json();
    if (
      typeof user.id !== "string" ||
      !validId(user.id) ||
      typeof user.username !== "string"
    )
      return failure("oauth");
    const ttl = Math.min(3600, token.expires_in);
    const id = saveSession({
      user: {
        id: user.id,
        name:
          typeof user.global_name === "string"
            ? user.global_name
            : user.username,
        avatar: typeof user.avatar === "string" ? user.avatar : null,
      },
      accessToken: token.access_token,
      expiresAt: Date.now() + ttl * 1000,
    });
    const response = NextResponse.redirect(new URL("/dashboard", config.base));
    response.cookies.set(SESSION_COOKIE, id, { ...cookieOptions, maxAge: ttl });
    response.cookies.set(STATE_COOKIE, "", { ...cookieOptions, maxAge: 0 });
    return response;
  } catch {
    return failure("oauth");
  }
}
