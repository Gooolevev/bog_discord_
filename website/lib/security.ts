import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
export type DiscordGuild = {
  id: string;
  name: string;
  icon: string | null;
  owner?: boolean;
  permissions?: string;
};
export function validId(value: string): boolean {
  return /^[1-9]\d{16,19}$/.test(value) && BigInt(value) < 2n ** 63n;
}
export function canManage(guild: DiscordGuild): boolean {
  if (guild.owner === true) return true;
  if (!guild.permissions || !/^\d+$/.test(guild.permissions)) return false;
  return (BigInt(guild.permissions) & (8n | 32n)) !== 0n;
}
export function createState(secret: string, now = Date.now()): string {
  const payload = `${randomBytes(24).toString("base64url")}.${now}`;
  return `${payload}.${createHmac("sha256", secret).update(payload).digest("base64url")}`;
}
export function verifyState(
  value: string,
  expected: string,
  secret: string,
  now = Date.now(),
): boolean {
  if (value.length > 200 || value !== expected) return false;
  const parts = value.split(".");
  if (parts.length !== 3 || !/^\d+$/.test(parts[1])) return false;
  const age = now - Number(parts[1]);
  if (age < 0 || age > 600_000) return false;
  const signature = createHmac("sha256", secret)
    .update(`${parts[0]}.${parts[1]}`)
    .digest("base64url");
  return (
    parts[2].length === signature.length &&
    timingSafeEqual(Buffer.from(parts[2]), Buffer.from(signature))
  );
}
export function isSameOrigin(origin: string | null, siteUrl: string): boolean {
  try {
    return (
      origin !== null && new URL(origin).origin === new URL(siteUrl).origin
    );
  } catch {
    return false;
  }
}
export function validateSettings(value: unknown): value is {
  monitor_enabled: boolean;
  monitor_channel_id: string;
  poll_minutes: number;
} {
  if (typeof value !== "object" || value === null) return false;
  const input = value as Record<string, unknown>;
  return (
    Object.keys(input).sort().join(",") ===
      "monitor_channel_id,monitor_enabled,poll_minutes" &&
    typeof input.monitor_enabled === "boolean" &&
    typeof input.monitor_channel_id === "string" &&
    (input.monitor_channel_id === "0" || validId(input.monitor_channel_id)) &&
    Number.isInteger(input.poll_minutes) &&
    Number(input.poll_minutes) >= 1 &&
    Number(input.poll_minutes) <= 1440 &&
    (!input.monitor_enabled || input.monitor_channel_id !== "0")
  );
}
