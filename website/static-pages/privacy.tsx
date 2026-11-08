import { Header } from "@/components/header";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "О ваших данных" };

export default function PublicPrivacy() {
  return (
    <>
      <Header />
      <main id="main" className="privacy-page">
        <span className="eyebrow">ПОНЯТНО И БЕЗ МЕЛКОГО ШРИФТА</span>
        <h1>О ваших данных.</h1>
        <p>Это публичный сайт на GitHub Pages. Вход через Discord и сохранение настроек бота здесь отключены.</p>
        <h2>Тема оформления</h2>
        <p>Выбранная тема сохраняется в вашем браузере. Рекламной аналитики на сайте нет.</p>
        <h2>Музыка</h2>
        <p>После загрузки плеера Spotify получает технические данные браузера и может использовать собственные cookie. Введённая ссылка на музыку не сохраняется в базе сайта.</p>
        <h2>Хостинг</h2>
        <p>Сайт размещён на GitHub Pages. Обработка технических данных при посещении регулируется политикой конфиденциальности GitHub.</p>
        <p>
          <a className="text-link" href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement">Политика GitHub</a>
          {" · "}
          <a className="text-link" href="https://www.spotify.com/legal/privacy-policy/">Политика Spotify</a>
        </p>
      </main>
    </>
  );
}
