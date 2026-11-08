import Link from "next/link";
import { ArrowDown, ArrowRight, ArrowUpRight, AudioLines, Check, ChevronRight, CircleHelp, Command, Hash, LayoutDashboard, Radio, ShieldCheck, SlidersHorizontal, Sparkles, Users, Waves } from "lucide-react";
import { Header } from "@/components/header";
import { Brand, DiscordIcon } from "@/components/brand";
import { SpotifyPlayer } from "@/components/spotify-player";
import { FAQ } from "@/components/faq";
import "./home.css";
function OrbitBot() {
  return (<div className="orbit-scene" role="img" aria-label="Парящий робот Discord Bot в окружении орбит">
    <div className="orbit-grid" />
    <div className="orbit-halo" />
    <div className="orbit-track track-one" />
    <div className="orbit-track track-two" />
    <div className="orbit-spark spark-one">+</div>
    <div className="orbit-spark spark-two">+</div>
    <div className="bot-object">
      <div className="bot-antenna">
        <i />
      </div>
      <div className="bot-ear ear-left" />
      <div className="bot-ear ear-right" />
      <div className="bot-head">
        <div className="bot-face">
          <i />
          <i />
          <span />
        </div>
        <div className="bot-cheek" />
      </div>
      <div className="bot-neck" />
      <div className="bot-body">
        <Waves size={30} strokeWidth={2.5} />
        <i />
      </div>
      <div className="bot-hand hand-left" />
      <div className="bot-hand hand-right" />
    </div>
    <div className="orbit-shadow" />
    <div className="orbit-tag tag-minecraft">
      <span className="tag-icon">
        <Radio size={18} />
      </span>
      <div>
        <strong>Minecraft</strong>
        <small>Ваш мир на связи</small>
      </div>
      <span className="orbit-led" />
    </div>
    <div className="orbit-tag tag-community">
      <span className="tag-icon">
        <Users size={18} />
      </span>
      <div>
        <strong>Свои люди. Общие планы.</strong>
        <small>Собирайтесь в Discord</small>
      </div>
    </div>
  </div>);
}
function PanelPreview() {
  return (<div className="panel-preview" aria-label="Демонстрация внешнего вида панели управления">
    <div className="preview-toolbar">
      <span className="preview-dots">
        <i />
        <i />
        <i />
      </span>
      <span>DISCORD BOT / ПАНЕЛЬ УПРАВЛЕНИЯ</span>
      <span className="preview-demo">ДЕМО</span>
    </div>
    <div className="preview-layout">
      <aside className="preview-sidebar">
        <span className="preview-server">
          <span>М</span> Мой сервер <ChevronRight size={14} />
        </span>
        <span className="preview-nav-active">
          <LayoutDashboard size={15} /> Обзор сервера</span>
        <span>
          <Radio size={15} /> Minecraft</span>
        <span>
          <Users size={15} /> Опросы</span>
        <span className="preview-side-bottom">
          <ShieldCheck size={14} /> Ваше пространство</span>
      </aside>
      <div className="preview-main">
        <div className="preview-heading">
          <div>
            <span className="micro-label">НАСТРОЙКИ СЕРВЕРА</span>
            <h3>Всё под контролем.</h3>
          </div>
          <span className="preview-avatar">М</span>
        </div>
        <div className="preview-banner">
          <span className="preview-banner-icon">
            <Radio size={24} />
          </span>
          <div>
            <strong>Ваш Minecraft. На радаре.</strong>
            <p>Уведомления о падении и восстановлении</p>
          </div>
        </div>
        <div className="preview-setting">
          <div>
            <strong>Мониторинг Minecraft</strong>
            <small>Проверка сервера раз в минуту</small>
          </div>
          <span className="preview-switch" aria-hidden="true" />
        </div>
        <div className="preview-setting">
          <div>
            <strong>Канал уведомлений</strong>
            <small>Здесь бот сообщит об изменениях</small>
          </div>
          <span className="preview-select">
            <Hash size={13} /> статус-сервера <ChevronRight size={12} />
          </span>
        </div>
        <div className="preview-setting">
          <div>
            <strong>Длительность опросов</strong>
            <small>Для новых голосований</small>
          </div>
          <span className="preview-select">60 минут <ChevronRight size={12} />
          </span>
        </div>
        <div className="preview-save">
          <span>
            <Check size={13} /> Пример настроек</span>
          <Link href="/dashboard">Открыть свою панель <ArrowUpRight size={13} />
          </Link>
        </div>
      </div>
    </div>
  </div>);
}
export default function Home() {
  return (<div className="kontur-home">
    <Header />
    <main id="main">
      <section className="landing-hero landing-width">
        <div className="landing-hero-copy">
          <div className="landing-kicker">
            <span /> DISCORD-БОТ ДЛЯ ВАШЕГО СООБЩЕСТВА</div>
          <h1>Ваш сервер.<br />Ваши люди.<br />
            <span>Discord Bot</span>
          </h1>
          <p>Собирайте команду, решайте вместе и держите Minecraft на радаре. Всё, что нужно вашим людям, — в одном боте.</p>
          <div className="landing-actions">
            <Link className="landing-button primary" href="/invite">
              <DiscordIcon /> Добавить в Discord <ArrowUpRight size={18} />
            </Link>
            <Link className="landing-button secondary" href="/dashboard">Открыть панель <ArrowRight size={17} />
            </Link>
          </div>
          <div className="landing-hero-note">
            <ShieldCheck size={15} />
            <span>Ваш сервер. Ваши настройки. Ваши правила.</span>
          </div>
        </div>
        <OrbitBot />
        <div className="hero-index">
          <a href="#features">ПОЗНАКОМИТЬСЯ БЛИЖЕ <ArrowDown size={14} />
          </a>
        </div>
      </section>
      <div className="capability-strip">
        <div className="landing-width">
          <span>
            <Users /> Общие решения</span>
          <i />
          <span>
            <Radio /> Minecraft на связи</span>
          <i />
          <span>
            <SlidersHorizontal /> Управление с сайта</span>
          <i />
          <span>
            <Command /> Команды в Discord</span>
        </div>
      </div>
      <section className="landing-width landing-features" id="features">
        <div className="landing-section-heading">
          <div>
            <h2>Маленький бот.<br />
              <span>Большая часть команды.</span>
            </h2>
          </div>
        </div>
        <div className="landing-feature-grid">
          <article className="landing-feature feature-decisions">
            <span className="landing-feature-icon">
              <Users size={23} />
            </span>
            <span className="feature-number">01</span>
            <h3>Вместе —<br />решается.</h3>
            <p>Опросы с кнопками и сбор команды с лимитом мест. Каждый голос на месте, каждый участник в списке.</p>
            <div className="mini-poll">
              <span>ДЕМОНСТРАЦИЯ ОПРОСА</span>
              <strong>Какой план на вечер?</strong>
              <div className="mini-poll-option selected">
                <span>Строим общий порт</span>
                <Check size={15} />
              </div>
              <div className="mini-poll-option">
                <span>Идём исследовать мир</span>
                <span className="mini-radio" />
              </div>
            </div>
            <span className="command-label">/poll <i /> /сбор</span>
          </article>
          <article className="landing-feature feature-world">
            <span className="landing-feature-icon">
              <Radio size={23} />
            </span>
            <span className="feature-number">02</span>
            <h3>Мир живёт.<br />Вы в курсе.</h3>
            <p>Статус Minecraft, адрес и игроки в одной карточке. Уведомления, когда сервер падает или возвращается.</p>
            <div className="world-art" aria-hidden="true">
              <div className="world-ring" />
              <div className="world-ring inner" />
              <div className="voxel">
                <span />
                <span />
                <span />
              </div>
              <i className="world-point" />
              <span className="world-art-label">ВАШ МИР НА РАДАРЕ</span>
            </div>
            <span className="command-label">/server <i /> /мониторинг</span>
          </article>
          <article className="landing-feature feature-settings">
            <span className="landing-feature-icon">
              <SlidersHorizontal size={23} />
            </span>
            <span className="feature-number">03</span>
            <h3>Настроено.<br />Под вас.</h3>
            <p>Канал уведомлений, мониторинг и время для опросов. Управляйте настройками в отдельной панели.</p>
            <div className="mini-settings" aria-hidden="true">
              <div>
                <span>Уведомления</span>
                <span className="preview-switch" />
              </div>
              <div>
                <span>Канал сервера</span>
                <span># minecraft</span>
              </div>
              <div>
                <span>Время на выбор</span>
                <span>60 мин</span>
              </div>
            </div>
            <Link className="landing-inline-link" href="/dashboard">К настройкам <ArrowUpRight size={16} />
            </Link>
          </article>
        </div>
      </section>
      <section className="landing-dashboard-section" id="control">
        <div className="landing-width">
          <div className="landing-section-heading">
            <div>
              <h2>Ваш сервер.<br />
                <span>Теперь и в браузере.</span>
              </h2>
            </div>
            <div className="landing-dashboard-copy">
              <p>Войдите через Discord, выберите свой сервер и настройте бота. Сохранённые параметры применяются без перезапуска.</p>
              <Link href="/dashboard" className="landing-inline-link">Открыть панель управления <ArrowUpRight size={16} />
              </Link>
            </div>
          </div>
          <PanelPreview />
          <p className="preview-disclaimer">
            <CircleHelp size={14} /> Это превью интерфейса. Настоящие данные доступны после входа через Discord.</p>
        </div>
      </section>
      <section className="landing-width landing-music" id="music">
        <div className="landing-music-copy">
          <span className="micro-label">БОНУС / СВОЙ САУНДТРЕК</span>
          <div className="landing-music-icon">
            <AudioLines size={30} />
          </div>
          <h2>Хорошо быть<br />
            <span>на одной волне.</span>
          </h2>
          <p>Музыка для долгих строек и разговоров до утра. Откройте свой плейлист в официальном проигрывателе Spotify.</p>
          <span className="landing-music-note">Ваш саундтрек — с первого захода.</span>
        </div>
        <SpotifyPlayer initialUrl={process.env.SPOTIFY_URL || ""} />
      </section>
      <section className="landing-width landing-start" id="start">
        <div className="landing-start-grid">
          <h2>Легко начать.<br />
            <span>Приятно остаться.</span>
          </h2>
          <ol>{[{ title: "Добавьте бота", text: "Пригласите Discord Bot на свой Discord-сервер." }, { title: "Откройте панель", text: "Войдите через Discord и выберите сервер с ботом." }, { title: "Настройте под себя", text: "Выберите канал и включите нужные уведомления." }].map((step, i) => <li key={step.title}>
            <span>0{i + 1}</span>
            <div>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </div>
            <ArrowUpRight size={18} />
          </li>)}</ol>
        </div>
      </section>
      <section className="landing-width landing-faq">
        <div>
          <span className="micro-label">ОСТАЛИСЬ ВОПРОСЫ?</span>
          <h2>Разберёмся.</h2>
        </div>
        <FAQ />
      </section>
      <section className="landing-width landing-final">
        <div>
          <span className="micro-label">ЛЮДИ УЖЕ ЕСТЬ. СОЕДИНИМ ИХ.</span>
          <h2>Ваша компания.<br />
            <span>В одном Discord.</span>
          </h2>
        </div>
        <div>
          <Link href="/invite" className="landing-button primary">
            <DiscordIcon /> Добавить в Discord <ArrowUpRight size={18} />
          </Link>
          <Link href="/dashboard" className="landing-inline-link">Уже с нами? В панель <ArrowRight size={15} />
          </Link>
        </div>
        <Sparkles className="final-spark" aria-hidden="true" />
      </section>
    </main>
    <footer className="landing-width landing-footer">
      <div>
        <Brand />
        <p>Точка сборки вашего сообщества.</p>
      </div>
      <nav aria-label="Навигация в подвале">
        <Link href="#features">Возможности</Link>
        <Link href="/dashboard">Панель управления</Link>
        <Link href="/privacy">Конфиденциальность</Link>
      </nav>
      <div className="landing-footer-bottom">
        <span>© {new Date().getFullYear()} Discord Bot</span>
        <span>СОЗДАН ДЛЯ ЛЮДЕЙ, КОТОРЫЕ ИГРАЮТ ВМЕСТЕ</span>
        <span>Не связан с Discord Inc.</span>
      </div>
    </footer>
  </div>);
}
