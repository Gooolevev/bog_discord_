import Link from "next/link";
import Image from "next/image";
import {
  ArrowUpRight,
  ArrowRight,
  ShieldCheck,
  Radio,
  Server,
  Wrench,
} from "lucide-react";
import { RefreshButton } from "@/components/refresh-button";
import { DiscordIcon } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { authConfig, getSession } from "@/lib/auth";
import { loadGuilds, serviceMessage, type GuildSummary } from "@/lib/bot-api";
const errors: Record<string, string> = {
  configuration: "Для входа нужно настроить Discord-приложение сайта.",
  state: "Проверка входа устарела. Начните вход ещё раз.",
  cancelled: "Вы отменили вход. Можно попробовать снова в любое время.",
  oauth: "Не удалось завершить вход через Discord. Попробуйте ещё раз.",
};
export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const config = authConfig();
  const session = await getSession();
  const params = await searchParams;
  if (!session)
    return (
      <>
        <div className="dashboard-heading">
          <div>
            <span className="eyebrow">ВАШ СЕРВЕР. ВАШИ ПРАВИЛА.</span>
            <h1>Всё важное — под рукой.</h1>
            <p className="dashboard-description">
              Немного настроек. Намного больше порядка.
            </p>
          </div>
        </div>
        <div className="panel-card panel-empty">
          <div className="empty-icon">
            <DiscordIcon className="size-8" />
          </div>
          <h2>Привет. Это ваше пространство.</h2>
          <p>
            Войдите через Discord, чтобы выбрать сервер и настроить Discord Bot. Мы
            покажем только серверы, которыми вы можете управлять и где уже есть
            бот.
          </p>
          {config.ready ? (
            <Button asChild className="button-mint" size="lg">
              <a href="/api/auth/login">
                <DiscordIcon /> Войти через Discord <ArrowUpRight size={16} />
              </a>
            </Button>
          ) : (
            <div className="config-note">
              <Wrench size={17} style={{ margin: "0 auto 10px" }} />
              <strong>Вход пока не настроен</strong>
              <p>
                Владельцу нужно добавить настройки OAuth2 в{" "}
                <code>website/.env.local</code>. Инструкция подготовлена в
                README проекта. Главная страница и музыкальный проигрыватель уже
                доступны.
              </p>
            </div>
          )}
          {params.error && (
            <p role="alert" className="form-error">
              {errors[params.error] || "Не удалось выполнить вход."}
            </p>
          )}
          <p className="config-note">
            <ShieldCheck
              size={14}
              style={{ display: "inline", marginRight: 5 }}
            />{" "}
            Пароль остаётся в Discord. Нам нужны только профиль и список
            серверов.
          </p>
          <Link href="/" className="text-link" style={{ marginTop: 25 }}>
            Вернуться на главную <ArrowRight size={14} />
          </Link>
        </div>
      </>
    );
  let guilds: GuildSummary[] = [];
  let problem = "";
  try {
    guilds = await loadGuilds();
  } catch (error) {
    problem = serviceMessage(error);
  }
  return (
    <>
      <div className="dashboard-heading">
        <div>
          <span className="eyebrow">ПРОСТРАНСТВО СООБЩЕСТВА</span>
          <h1>Ваши маленькие вселенные.</h1>
          <p className="dashboard-description">
            Выберите сервер, чтобы настроить уведомления и опросы.
          </p>
        </div>
        <span className="status-badge">
          <ShieldCheck size={13} /> Доступ проверяется в Discord
        </span>
      </div>
      {problem ? (
        <div className="panel-card panel-empty">
          <div className="empty-icon">
            <Radio size={28} />
          </div>
          <h2>Пока нет связи.</h2>
          <p role="alert">{problem}</p>
          <div style={{ marginTop: 24 }}>
            <RefreshButton />
          </div>
        </div>
      ) : guilds.length ? (
        <div className="guild-grid">
          {guilds.map((guild) => (
            <Link
              key={guild.id}
              href={`/dashboard/${guild.id}`}
              className="panel-card guild-card"
            >
              <span className="guild-avatar">
                {guild.icon ? (
                  <Image src={guild.icon} alt="" width={48} height={48} />
                ) : (
                  guild.name[0]
                )}
              </span>
              <div>
                <h2>{guild.name}</h2>
                <p>
                  {guild.member_count === null
                    ? "Сервер Discord"
                    : `${guild.member_count} участников`}{" "}
                  · Discord Bot установлен
                </p>
              </div>
              <ArrowUpRight size={18} />
            </Link>
          ))}
        </div>
      ) : (
        <div className="panel-card panel-empty">
          <div className="empty-icon">
            <Server size={28} />
          </div>
          <h2>Здесь будет ваш сервер.</h2>
          <p>
            Пока нет серверов с установленным Discord Bot и вашим правом
            управления. Пригласите бота или попросите владельца выдать право
            «Управление сервером».
          </p>
          <Button asChild className="button-mint" style={{ marginTop: 24 }}>
            <Link href="/invite">
              Пригласить бота <ArrowUpRight size={15} />
            </Link>
          </Button>
          <div style={{ marginTop: 18 }}>
            <RefreshButton label="Обновить список" />
          </div>
        </div>
      )}
    </>
  );
}
