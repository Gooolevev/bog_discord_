import { NextRequest, NextResponse } from "next/server";
import {
  authConfig,
  cookieOptions,
  deleteSession,
  SESSION_COOKIE,
} from "@/lib/auth";
import { isSameOrigin } from "@/lib/security";
export async function POST(request: NextRequest) {
  const config = authConfig();
  if (!isSameOrigin(request.headers.get("origin"), config.base))
    return NextResponse.json({ error: "Запрос отклонён." }, { status: 403 });
  await deleteSession();
  const response = NextResponse.redirect(
    new URL("/dashboard", config.base),
    303,
  );
  response.cookies.set(SESSION_COOKIE, "", { ...cookieOptions, maxAge: 0 });
  return response;
}
