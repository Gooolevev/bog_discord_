import { NextRequest, NextResponse } from "next/server";
import { authConfig } from "@/lib/auth";
import {
  botRequest,
  loadGuild,
  requireGuild,
  ServiceError,
  serviceMessage,
} from "@/lib/bot-api";
import { isSameOrigin, validateSettings } from "@/lib/security";
function failure(error: unknown) {
  return NextResponse.json(
    { error: serviceMessage(error) },
    {
      status: error instanceof ServiceError ? error.status : 500,
      headers: { "Cache-Control": "no-store" },
    },
  );
}
export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ guildId: string }> },
) {
  try {
    return NextResponse.json(await loadGuild((await context.params).guildId), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    return failure(error);
  }
}
export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ guildId: string }> },
) {
  if (!isSameOrigin(request.headers.get("origin"), authConfig().base))
    return NextResponse.json(
      { error: "Запрос отклонён. Обновите страницу." },
      { status: 403 },
    );
  if (
    !request.headers.get("content-type")?.startsWith("application/json") ||
    Number(request.headers.get("content-length") || 0) > 4096
  )
    return NextResponse.json(
      { error: "Некорректный запрос." },
      { status: 400 },
    );
  try {
    const { guildId } = await context.params;
    const session = await requireGuild(guildId);
    let body: unknown;
    try {
      const text = await request.text();
      if (text.length > 4096) throw new Error();
      body = JSON.parse(text);
    } catch {
      throw new ServiceError(400, "Некорректные настройки.");
    }
    if (!validateSettings(body))
      throw new ServiceError(
        400,
        "Проверьте канал и длительность опросов (1–1440 минут).",
      );
    return NextResponse.json(
      await botRequest(`/guilds/${guildId}?user_id=${session.user.id}`, {
        method: "PUT",
        body: JSON.stringify(body),
      }),
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    return failure(error);
  }
}
