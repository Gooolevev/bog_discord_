"use client";
import { useEffect, useState } from "react";
import { Check, LoaderCircle, Save, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { GuildSettings } from "@/lib/bot-api";
type Values = Pick<
  GuildSettings,
  "monitor_enabled" | "monitor_channel_id" | "poll_minutes"
>;
export function SettingsForm({
  guildId,
  initial,
  channels,
}: {
  guildId: string;
  initial: GuildSettings;
  channels: { id: string; name: string }[];
}) {
  const [saved, setSaved] = useState<Values>({
    monitor_enabled: initial.monitor_enabled,
    monitor_channel_id: initial.monitor_channel_id,
    poll_minutes: initial.poll_minutes,
  });
  const [values, setValues] = useState<Values>(saved);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<{
    ok: boolean;
    text: string;
  } | null>(null);
  const dirty = JSON.stringify(values) !== JSON.stringify(saved);
  useEffect(() => {
    if (!dirty) return;
    const before = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", before);
    return () => window.removeEventListener("beforeunload", before);
  }, [dirty]);
  function change<T extends keyof Values>(key: T, value: Values[T]) {
    setValues((v) => ({ ...v, [key]: value }));
    setFeedback(null);
  }
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (busy || !dirty) return;
    if (values.monitor_enabled && values.monitor_channel_id === "0") {
      setFeedback({ ok: false, text: "Выберите канал для уведомлений." });
      return;
    }
    setBusy(true);
    setFeedback(null);
    try {
      const response = await fetch(`/api/guilds/${guildId}/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
        signal: AbortSignal.timeout(25000),
      });
      const result = await response.json();
      if (!response.ok)
        throw new Error(
          typeof result.error === "string"
            ? result.error
            : "Не удалось сохранить настройки.",
        );
      setSaved({ ...values });
      setFeedback({
        ok: true,
        text: "Сохранено. Бот уже использует новые настройки.",
      });
    } catch (error) {
      setFeedback({
        ok: false,
        text:
          error instanceof Error && error.name !== "TimeoutError"
            ? error.message
            : "Не удалось дождаться ответа. Обновите страницу и проверьте настройки.",
      });
    } finally {
      setBusy(false);
    }
  }
  const options = [15, 30, 60, 120, 360, 720, 1440];
  if (!options.includes(values.poll_minutes)) options.push(values.poll_minutes);
  options.sort((a, b) => a - b);
  return (
    <form className="settings-form" onSubmit={save}>
      <section className="panel-card">
        <h2>Настроить под своих.</h2>
        <p>Только то, что действительно влияет на работу бота.</p>
        <div className="setting-row">
          <div>
            <label htmlFor="monitor-switch">Наблюдать за Minecraft</label>
            <p>
              Бот проверит сервер раз в минуту и сообщит о падении или
              восстановлении.
            </p>
          </div>
          <Switch
            id="monitor-switch"
            checked={values.monitor_enabled}
            onCheckedChange={(v) => change("monitor_enabled", v)}
            disabled={busy}
          />
        </div>
        <div className="setting-row">
          <div>
            <label htmlFor="monitor-channel">Канал уведомлений</label>
            <p>
              Показываем текстовые каналы, в которых бот может отправлять
              Embed-сообщения.
            </p>
          </div>
          <div className="setting-control">
            <Select
              value={values.monitor_channel_id}
              onValueChange={(v) => change("monitor_channel_id", v)}
              disabled={busy}
            >
              <SelectTrigger id="monitor-channel">
                <SelectValue placeholder="Выберите канал" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="0">Не выбран</SelectItem>
                {channels.map((channel) => (
                  <SelectItem key={channel.id} value={channel.id}>
                    # {channel.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="setting-row">
          <div>
            <label htmlFor="poll-minutes">Время на общий выбор</label>
            <p>
              Длительность новых опросов по умолчанию. В конкретном опросе её
              можно изменить. Текущие опросы сохранят свой срок.
            </p>
          </div>
          <div className="setting-control">
            <Select
              value={String(values.poll_minutes)}
              onValueChange={(v) => change("poll_minutes", Number(v))}
              disabled={busy}
            >
              <SelectTrigger id="poll-minutes">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {options.map((minutes) => (
                  <SelectItem key={minutes} value={String(minutes)}>
                    {minutes >= 60 && minutes % 60 === 0
                      ? `${minutes / 60} ч`
                      : `${minutes} мин`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </section>
      <div className="settings-footer">
        <p>
          {dirty
            ? "Есть несохранённые изменения"
            : "Настройки синхронизированы"}
        </p>
        <div style={{ display: "flex", gap: 10 }}>
          <Button
            type="button"
            variant="ghost"
            disabled={!dirty || busy}
            onClick={() => {
              setValues({ ...saved });
              setFeedback(null);
            }}
          >
            Сбросить
          </Button>
          <Button
            type="submit"
            className="button-mint"
            disabled={!dirty || busy}
          >
            {busy ? (
              <LoaderCircle className="animate-spin" size={15} />
            ) : (
              <Save size={15} />
            )}{" "}
            {busy ? "Сохраняем…" : "Сохранить"}
          </Button>
        </div>
      </div>
      {feedback && (
        <p
          role={feedback.ok ? "status" : "alert"}
          className={`settings-status ${feedback.ok ? "success" : "error"}`}
        >
          {feedback.ok && <Check size={15} />} {feedback.text}
        </p>
      )}
      <p
        className="settings-status"
        style={{ color: "var(--muted)", fontSize: 9 }}
      >
        <ShieldCheck size={13} /> Права управления проверяются при каждом
        сохранении.
      </p>
    </form>
  );
}
