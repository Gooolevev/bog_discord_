"use client";
import { useState } from "react";
import {
  Hash,
  Volume2,
  ChevronDown,
  Plus,
  Headphones,
  Mic,
  Users,
  Check,
  ArrowUpRight,
  BarChart3,
  Gamepad2,
  RotateCcw,
  CircleHelp,
} from "lucide-react";
import { DiscordIcon } from "@/components/brand";
type Tab = "poll" | "party" | "minecraft";
const tabs: { id: Tab; label: string; icon: typeof Users }[] = [
  { id: "poll", label: "Решить вместе", icon: BarChart3 },
  { id: "party", label: "Собрать команду", icon: Users },
  { id: "minecraft", label: "Зайти в Minecraft", icon: Gamepad2 },
];
export function DiscordDemo() {
  const [tab, setTab] = useState<Tab>("poll");
  const [vote, setVote] = useState<number | null>(null);
  const [joined, setJoined] = useState(false);
  const [refreshed, setRefreshed] = useState(false);
  const [connect, setConnect] = useState(false);
  const [closed, setClosed] = useState(false);
  const [notice, setNotice] = useState("");
  const options = ["Общий порт", "Автоматическая ферма", "Новый спавн"];
  const base = [8, 5, 3];
  const counts = base.map((n, i) => n + (vote === i ? 1 : 0));
  const total = counts.reduce((a, b) => a + b, 0);
  function reset() {
    setVote(null);
    setJoined(false);
    setClosed(false);
    setRefreshed(false);
    setConnect(false);
    setNotice("");
  }
  return (
    <div className="playground">
      <div
        className="demo-tabs"
        role="tablist"
        aria-label="Возможности бота"
        onKeyDown={(event) => {
          const current = tabs.findIndex((item) => item.id === tab);
          const next =
            event.key === "ArrowRight"
              ? (current + 1) % tabs.length
              : event.key === "ArrowLeft"
                ? (current + tabs.length - 1) % tabs.length
                : event.key === "Home"
                  ? 0
                  : event.key === "End"
                    ? tabs.length - 1
                    : -1;
          if (next < 0) return;
          event.preventDefault();
          setTab(tabs[next].id);
          setNotice("");
          document.getElementById(`tab-${tabs[next].id}`)?.focus();
        }}
      >
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            role="tab"
            aria-selected={tab === id}
            tabIndex={tab === id ? 0 : -1}
            aria-controls="demo-panel"
            id={`tab-${id}`}
            onClick={() => {
              setTab(id);
              setNotice("");
            }}
            className={tab === id ? "demo-tab active" : "demo-tab"}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>
      <div className="discord-window">
        <div className="window-top">
          <div className="window-dots">
            <i />
            <i />
            <i />
          </div>
          <span>
            <DiscordIcon /> Ваш сервер · пространство сообщества
          </span>
          <span className="demo-label">ДЕМОНСТРАЦИЯ</span>
        </div>
        <div className="discord-content">
          <aside className="discord-servers" aria-hidden="true">
            <div className="discord-server-logo">
              <DiscordIcon />
            </div>
            <div className="server-divider" />
            <div className="server-current">К</div>
            <div className="server-round">✦</div>
            <div className="server-round server-add">
              <Plus size={22} />
            </div>
          </aside>
          <aside className="discord-channels" aria-hidden="true">
            <div className="channel-server">
              Наша маленькая вселенная <ChevronDown size={14} />
            </div>
            <div className="channel-list">
              <span className="channel-category">⌄ ИНФОРМАЦИЯ</span>
              <span>
                <Hash size={16} /> добро-пожаловать
              </span>
              <span>
                <Hash size={16} /> объявления
              </span>
              <span className="channel-category">⌄ ОБЩЕНИЕ</span>
              <span className="channel-selected">
                <Hash size={16} /> общее
              </span>
              <span>
                <Hash size={16} /> наши-планы
              </span>
              <span>
                <Hash size={16} /> minecraft
              </span>
              <span className="channel-category">⌄ ГОЛОСОВЫЕ КАНАЛЫ</span>
              <span>
                <Volume2 size={16} /> Гостиная
              </span>
              <div className="voice-person">
                <i className="avatar avatar-peach">С</i> Саша
              </div>
              <div className="voice-person">
                <i className="avatar avatar-lilac">К</i> Катя
              </div>
            </div>
            <div className="discord-you">
              <i className="avatar avatar-blue">В</i>
              <span>
                Вы <small>В хорошем настроении</small>
              </span>
              <Mic size={13} />
              <Headphones size={13} />
            </div>
          </aside>
          <div className="discord-main">
            <div className="discord-channel-title">
              <span>
                <Hash size={20} /> общее <i /> Здесь начинается хорошая компания
              </span>
              <Users size={18} />
            </div>
            <div className="discord-messages">
              <div className="demo-date">
                <span>СЕГОДНЯ В ВАШЕМ СООБЩЕСТВЕ</span>
              </div>
              <div className="chat-message">
                <i className="avatar avatar-peach">С</i>
                <div>
                  <div className="message-author">
                    Саша <time>Сегодня, 18:42</time>
                  </div>
                  <p>
                    {tab === "poll"
                      ? "Ну что, чем займёмся на выходных? 👀"
                      : tab === "party"
                        ? "Давайте наконец построим ту самую ферму!"
                        : "Кто со мной в наш мир?"}
                  </p>
                </div>
              </div>
              <div className="chat-command">
                <span>Вы использовали</span>{" "}
                <code>
                  /
                  {tab === "poll"
                    ? "poll"
                    : tab === "party"
                      ? "сбор"
                      : "server"}
                </code>
              </div>
              <div className="chat-message bot-message">
                <div className="bot-avatar">
                  <svg viewBox="0 0 40 40" fill="none">
                    <ellipse
                      cx="20"
                      cy="20"
                      rx="14"
                      ry="6"
                      transform="rotate(-42 20 20)"
                    />
                    <ellipse
                      cx="20"
                      cy="20"
                      rx="14"
                      ry="6"
                      transform="rotate(42 20 20)"
                    />
                  </svg>
                </div>
                <div className="bot-message-content">
                  <div className="message-author">
                    Discord Bot{" "}
                    <span className="bot-tag">
                      <Check size={9} /> APP
                    </span>
                    <time>Сегодня, 18:42</time>
                  </div>
                  <div
                    className={`bot-embed ${tab}`}
                    role="tabpanel"
                    id="demo-panel"
                    aria-labelledby={`tab-${tab}`}
                    tabIndex={0}
                  >
                    <div className="bot-embed-label">
                      <span className="small-dot" />
                      {tab === "poll"
                        ? closed
                          ? "ОПРОС · ИТОГИ"
                          : "ОПРОС · РЕШАЕМ ВМЕСТЕ"
                        : tab === "party"
                          ? "СБОР · ЕСТЬ ДЕЛО"
                          : "MINECRAFT · МОЖНО ЗАХОДИТЬ"}
                    </div>
                    <h3>
                      {tab === "poll"
                        ? "Что построим вместе?"
                        : tab === "party"
                          ? "Большая стройка: общая ферма"
                          : "Мир на месте. Не хватает только вас."}
                    </h3>
                    {tab === "poll" ? (
                      <>
                        <p className="embed-intro">
                          Хорошие идеи заслуживают общего решения.
                        </p>
                        <div className="vote-options">
                          {options.map((option, i) => (
                            <button
                              type="button"
                              key={option}
                              disabled={closed}
                              className={
                                vote === i
                                  ? "vote-option selected"
                                  : "vote-option"
                              }
                              onClick={() => {
                                setVote(vote === i ? null : i);
                                setNotice(
                                  vote === i ? "Голос снят" : "Ваш голос учтён",
                                );
                              }}
                            >
                              <span className="vote-option-top">
                                <span>{option}</span>
                                <b>
                                  {Math.round((counts[i] / total) * 100)}%{" "}
                                  {vote === i && <Check size={13} />}
                                </b>
                              </span>
                              <span className="vote-track">
                                <span
                                  style={{
                                    width: `${(counts[i] / total) * 100}%`,
                                  }}
                                />
                              </span>
                            </button>
                          ))}
                        </div>
                        <div className="embed-bottom">
                          <span>
                            <Users size={13} /> {total} голосов
                          </span>
                          <span>
                            {closed
                              ? "Выбрано: Общий порт"
                              : "Итоги через 1 час"}
                          </span>
                        </div>
                      </>
                    ) : tab === "party" ? (
                      <>
                        <p className="embed-intro">
                          Берите кирки, захватите хорошее настроение.
                        </p>
                        <div className="party-slots">
                          {[
                            "Саша",
                            "Катя",
                            "Макс",
                            ...(joined ? ["Вы"] : []),
                          ].map((name, i) => (
                            <span key={name}>
                              <i
                                className={`avatar ${i % 2 ? "avatar-lilac" : "avatar-peach"}`}
                              >
                                {name[0]}
                              </i>
                              {name}
                            </span>
                          ))}
                          {!joined && (
                            <span className="empty-slot">
                              <Plus size={16} /> Ваше место
                            </span>
                          )}
                        </div>
                        <div className="embed-bottom">
                          <span>
                            <Users size={13} /> {joined ? 4 : 3} из 5 мест
                          </span>
                          <span>Начало через 30 минут</span>
                        </div>
                      </>
                    ) : (
                      <>
                        <p className="embed-intro">
                          Пример статуса сервера. Никаких реальных подключений.
                        </p>
                        <div className="mc-stats">
                          <span>
                            <small>ИГРОКИ</small>
                            <strong>
                              12<span>/ 20</span>
                            </strong>
                          </span>
                          <span>
                            <small>ВЕРСИЯ</small>
                            <strong>1.21</strong>
                          </span>
                          <span>
                            <small>ОТКЛИК</small>
                            <strong>
                              24 <span>мс</span>
                            </strong>
                          </span>
                        </div>
                        <div className="mc-address">
                          <span className="small-dot" /> play.example.org{" "}
                          <span>Java Edition</span>
                        </div>
                        {connect && (
                          <p className="demo-connect">
                            В игре: «Сетевая игра» → «Добавить сервер». Адрес
                            выше — пример для демонстрации.
                          </p>
                        )}
                      </>
                    )}
                    <div className="embed-footer">
                      <span className="mini-orbit">◎</span> СООБЩЕСТВО · меньше
                      суеты, больше совместных дел
                    </div>
                  </div>
                  <div className="bot-buttons">
                    {tab === "poll" ? (
                      <>
                        <button
                          className="discord-button primary"
                          disabled={closed}
                          onClick={() => {
                            setVote(vote === null ? 0 : null);
                            setNotice(
                              vote === null
                                ? "Голос за общий порт сохранён. Можно выбрать другой вариант выше."
                                : "Голос снят",
                            );
                          }}
                        >
                          {vote === null ? "Проголосовать" : "Снять голос"}
                        </button>
                        <button
                          className="discord-button"
                          disabled={closed}
                          onClick={() => {
                            setClosed(true);
                            setNotice("Опрос завершён. Победил общий порт.");
                          }}
                        >
                          Завершить
                        </button>
                      </>
                    ) : tab === "party" ? (
                      <button
                        className={`discord-button ${joined ? "" : "green"}`}
                        onClick={() => {
                          setJoined(!joined);
                          setNotice(
                            joined
                              ? "Вы вышли из команды"
                              : "Вы в команде. До встречи на стройке!",
                          );
                        }}
                      >
                        {joined ? <Check size={13} /> : <Plus size={13} />}{" "}
                        {joined ? "Выйти из команды" : "Я участвую"}
                      </button>
                    ) : (
                      <>
                        <button
                          className="discord-button primary"
                          onClick={() => {
                            setRefreshed(true);
                            setNotice("Демонстрационный статус обновлён");
                          }}
                        >
                          <RotateCcw size={12} />{" "}
                          {refreshed ? "Обновлено" : "Обновить"}
                        </button>
                        <button
                          className="discord-button"
                          onClick={() => setConnect(!connect)}
                        >
                          Как подключиться <ArrowUpRight size={12} />
                        </button>
                      </>
                    )}
                  </div>
                  <div
                    className="demo-feedback"
                    role="status"
                    aria-live="polite"
                  >
                    {notice}
                  </div>
                </div>
              </div>
            </div>
            <div className="discord-message-input">
              <Plus size={17} />
              <span>Хорошие разговоры начинаются здесь</span>
              <span>✦</span>
            </div>
          </div>
          <aside className="discord-members" aria-hidden="true">
            <span className="channel-category">НА СВЯЗИ — 4</span>
            <div>
              <i className="avatar bot-small">◎</i>
              <span>
                Discord Bot <small>Забочусь о деталях</small>
              </span>
            </div>
            <div>
              <i className="avatar avatar-peach">С</i>
              <span>Саша</span>
            </div>
            <div>
              <i className="avatar avatar-lilac">К</i>
              <span>Катя</span>
            </div>
            <div>
              <i className="avatar avatar-blue">М</i>
              <span>Макс</span>
            </div>
            <div className="members-note">
              <Headphones size={22} />
              <p>
                Хорошо, когда
                <br />
                все рядом.
              </p>
            </div>
          </aside>
        </div>
      </div>
      <div className="demo-under">
        <span>
          <CircleHelp size={14} /> Это интерактивный пример. Данные вымышлены,
          возможности — настоящие.
        </span>
        <button onClick={reset}>
          <RotateCcw size={12} /> Начать заново
        </button>
      </div>
    </div>
  );
}
