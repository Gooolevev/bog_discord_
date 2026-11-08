import "server-only";
import { getSession, type Session } from "@/lib/auth";
import { canManage, validId, type DiscordGuild } from "@/lib/security";
export class ServiceError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export type GuildSummary = {
  id: string;
  name: string;
  icon: string | null;
  member_count: number | null;
};
export type GuildSettings = {
  guild_id?: string;
  monitor_enabled: boolean;
  monitor_channel_id: string;
  poll_minutes: number;
};
export type GuildDetails = {
  guild: GuildSummary;
  settings: GuildSettings;
  channels: { id: string; name: string }[];
  bot: { ready: boolean; latency_ms: number | null };
};
export async function requireSession(): Promise<Session> {
  const session = await getSession();
  if (!session)
    throw new ServiceError(401, "Войдите через Discord, чтобы продолжить.");
  return session;
}
async function userGuilds(session: Session): Promise<DiscordGuild[]> {
  let response: Response;
  try {
    response = await fetch("https://discord.com/api/v10/users/@me/guilds", {
      headers: { Authorization: `Bearer ${session.accessToken}` },
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
  } catch {
    throw new ServiceError(
      503,
      "Discord сейчас не отвечает. Попробуйте немного позже.",
    );
  }
  if (response.status === 401)
    throw new ServiceError(401, "Вход устарел. Войдите через Discord ещё раз.");
  if (!response.ok)
    throw new ServiceError(
      503,
      "Не удалось проверить права в Discord. Попробуйте позже.",
    );
  const data: unknown = await response.json();
  if (!Array.isArray(data))
    throw new ServiceError(503, "Discord вернул некорректный список серверов.");
  return data.filter(
    (item): item is DiscordGuild =>
      typeof item === "object" &&
      item !== null &&
      typeof item.id === "string" &&
      validId(item.id),
  );
}
export async function requireGuild(guildId: string): Promise<Session> {
  if (!validId(guildId)) throw new ServiceError(400, "Некорректный сервер.");
  const session = await requireSession();
  if (
    !(await userGuilds(session)).some((g) => g.id === guildId && canManage(g))
  )
    throw new ServiceError(403, "У вас нет права управления этим сервером.");
  return session;
}
export async function botRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const secret = process.env.BOT_API_SECRET || "";
  const address = process.env.BOT_API_URL || "http://127.0.0.1:8081";
  let base: URL;
  try {
    base = new URL(address);
  } catch {
    throw new ServiceError(503, "Подключение к боту пока не настроено.");
  }
  if (
    secret.length < 32 ||
    !["127.0.0.1", "localhost", "[::1]"].includes(base.hostname) ||
    !["http:", "https:"].includes(base.protocol) ||
    base.username ||
    base.password ||
    base.pathname !== "/"
  )
    throw new ServiceError(503, "Закрытый API бота пока не настроен.");
  let response: Response;
  try {
    response = await fetch(new URL(path, base), {
      ...init,
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...init.headers,
        Authorization: `Bearer ${secret}`,
      },
      signal: AbortSignal.timeout(15000),
    });
  } catch {
    throw new ServiceError(
      503,
      "Не удалось связаться с ботом. Проверьте, что он запущен вместе с внутренним API.",
    );
  }
  if (!response.ok) {
    const messages: Record<number, string> = {
      400: "Проверьте канал уведомлений и значения настроек.",
      403: "Недостаточно прав для управления сервером.",
      404: "Бот или выбранный сервер недоступен.",
      503: "Бот пока не готов или Discord временно недоступен.",
    };
    throw new ServiceError(
      response.status === 401 ? 503 : response.status,
      messages[response.status] ||
        "Бот не смог обработать запрос. Попробуйте позже.",
    );
  }
  return response.json() as Promise<T>;
}
export async function loadGuilds(): Promise<GuildSummary[]> {
  const session = await requireSession();
  const allowed = (await userGuilds(session))
    .filter(canManage)
    .map((g) => g.id)
    .slice(0, 200);
  if (!allowed.length) return [];
  return (
    await botRequest<{ guilds: GuildSummary[] }>("/guilds", {
      method: "POST",
      body: JSON.stringify({ user_id: session.user.id, guild_ids: allowed }),
    })
  ).guilds;
}
export async function loadGuild(guildId: string): Promise<GuildDetails> {
  const session = await requireGuild(guildId);
  return botRequest<GuildDetails>(
    `/guilds/${guildId}?user_id=${session.user.id}`,
  );
}
export function serviceMessage(error: unknown): string {
  return error instanceof ServiceError
    ? error.message
    : "Не удалось загрузить данные. Попробуйте ещё раз.";
}
