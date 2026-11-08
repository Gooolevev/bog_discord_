import Link from "next/link";
import { Header } from "@/components/header";
import { Button } from "@/components/ui/button";
export default function NotFound() {
  return (
    <>
      <Header />
      <main id="main" className="auth-screen">
        <div className="panel-card panel-empty">
          <span className="eyebrow">404 / НЕ ТОТ КАНАЛ</span>
          <h2 style={{ marginTop: 20 }}>Кажется, здесь тихо.</h2>
          <p>Такой страницы нет. На главной точно есть хорошая компания.</p>
          <Button asChild className="button-mint" style={{ marginTop: 25 }}>
            <Link href="/">На главную</Link>
          </Button>
        </div>
      </main>
    </>
  );
}
