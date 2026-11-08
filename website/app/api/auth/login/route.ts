import { NextResponse } from "next/server";
import { authConfig, cookieOptions, STATE_COOKIE } from "@/lib/auth";
import { createState } from "@/lib/security";
export async function GET() {
  const config = authConfig();
  if (!config.ready)
    return NextResponse.redirect(
      new URL("/dashboard?error=configuration", config.base),
    );
  const state = createState(config.sessionSecret);
  const url = new URL("https://discord.com/oauth2/authorize");
  url.search = new URLSearchParams({
    client_id: config.id,
    redirect_uri: `${config.base}/api/auth/callback`,
    response_type: "code",
    scope: "identify guilds",
    state,
  }).toString();
  const response = NextResponse.redirect(url);
  response.cookies.set(STATE_COOKIE, state, { ...cookieOptions, maxAge: 600 });
  return response;
}
