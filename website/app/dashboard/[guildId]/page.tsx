import Link from "next/link";
import { ArrowLeft, Radio, ShieldAlert } from "lucide-react";
import {
  loadGuild,
  ServiceError,
  serviceMessage,
  type GuildDetails,
} from "@/lib/bot-api";
import { SettingsForm } from "@/components/settings-form";
import { Button } from "@/components/ui/button";
export default async function ServerPage({
  params,
}: {
  params: Promise<{ guildId: string }>;
}) {
  const { guildId } = await params;
  let data: GuildDetails;
  try {
    data = await loadGuild(guildId);
  } catch (error) {
    return (
      <div className="panel-card panel-empty">
        <div className="empty-icon">
          <ShieldAlert size={28} />
        </div>
        <h2>
          {error instanceof ServiceError && [401, 403].includes(error.status)
            ? "Проверим доступ?"
            : "Нет связи с сервером."}
        </h2>
        <p role="alert">{serviceMessage(error)}</p>
        <Button asChild variant="outline" style={{ marginTop: 25 }}>
          <Link href="/dashboard">
            <ArrowLeft size={15} /> К списку серверов
          </Link>
        </Button>
      </div>
    );
  }
  return (
    <>
      <Link
        href="/dashboard"
        className="text-link"
        style={{ marginBottom: 25, color: "var(--muted)" }}
      >
        <ArrowLeft size={13} /> Все серверы
      </Link>
      <div className="dashboard-heading">
        <div>
          <span className="eyebrow">СВОЙ СЕРВЕР. СВОЙ DISCORD BOT.</span>
          <h1>{data.guild.name}</h1>
          <p className="dashboard-description">
            Настройки применяются без перезапуска. Общение продолжается.
          </p>
        </div>
        <span className="status-badge">
          <span className="status-dot" /> Бот на связи
        </span>
      </div>
      <div className="settings-overview">
        <div className="panel-card">
          <small>СОСТОЯНИЕ</small>
          <strong>
            <Radio size={18} /> {data.bot.ready ? "На связи" : "Подключается"}
          </strong>
        </div>
        <div className="panel-card">
          <small>ЗАДЕРЖКА DISCORD</small>
          <strong>
            {data.bot.latency_ms === null ? "—" : `${data.bot.latency_ms} мс`}
          </strong>
        </div>
        <div className="panel-card">
          <small>УЧАСТНИКИ СЕРВЕРА</small>
          <strong>{data.guild.member_count ?? "—"}</strong>
        </div>
      </div>
      <SettingsForm
        guildId={guildId}
        initial={data.settings}
        channels={data.channels}
      />
    </>
  );
}
