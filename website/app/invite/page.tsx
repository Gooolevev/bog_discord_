import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { ArrowLeft, Wrench } from "lucide-react";
import { Header } from "@/components/header";
import { Button } from "@/components/ui/button";
export const metadata: Metadata = {
  title: "Добавить в Discord",
  robots: { index: false },
};
export default function InvitePage() {
  const id = process.env.DISCORD_CLIENT_ID;
  if (id && /^\d{17,20}$/.test(id))
    redirect(
      `https://discord.com/oauth2/authorize?${new URLSearchParams({ client_id: id, scope: "bot applications.commands", permissions: "19456" })}`,
    );
  return (
    <>
      <Header />
      <main id="main" className="auth-screen">
        <div className="panel-card panel-empty">
          <div className="empty-icon">
            <Wrench size={28} />
          </div>
          <h2>Готовим приглашение.</h2>
          <p>
            Для рабочей ссылки владельцу нужно указать{" "}
            <code>DISCORD_CLIENT_ID</code> в настройках сайта. Это публичный ID
            приложения бота из Discord Developer Portal.
          </p>
          <p>
            Токен бота для приглашения не нужен. Главную страницу и демонстрацию
            можно посмотреть уже сейчас.
          </p>
          <Button asChild variant="outline" style={{ marginTop: 24 }}>
            <Link href="/">
              <ArrowLeft size={15} /> Вернуться на главную
            </Link>
          </Button>
        </div>
      </main>
    </>
  );
}
