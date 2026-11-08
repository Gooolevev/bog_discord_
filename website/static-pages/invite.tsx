import Link from "next/link";
import type { Metadata } from "next";
import { Header } from "@/components/header";

export const metadata: Metadata = { title: "Приглашение бота" };

export default function InvitePreview() {
  return (
    <>
      <Header />
      <main id="main" className="privacy-page">
        <span className="eyebrow">ЗНАКОМИМСЯ БЛИЖЕ</span>
        <h1>Сначала — знакомство.</h1>
        <p>
          Сейчас опубликован сайт без подключения бота. Приглашение на сервер
          станет доступно на следующем этапе.
        </p>
        <Link href="/#features" className="landing-button primary">Изучить возможности</Link>
      </main>
    </>
  );
}
