import Link from "next/link";
import type { Metadata } from "next";
import { Header } from "@/components/header";

export const metadata: Metadata = {
  title: "Панель — следующий шаг",
  robots: { index: false, follow: false },
};

export default function DashboardPreview() {
  return (
    <>
      <Header />
      <main id="main" className="privacy-page">
        <span className="eyebrow">САЙТ УЖЕ НА СВЯЗИ</span>
        <h1>Панель — следующий шаг.</h1>
        <p>
          Сейчас здесь работает публичная версия сайта. Вход через Discord и
          настройки сервера появятся после подключения работающего бота.
        </p>
        <p>На главной можно посмотреть внешний вид панели и послушать музыку через Spotify.</p>
        <Link href="/#control" className="landing-button primary">Посмотреть демонстрацию</Link>
      </main>
    </>
  );
}
