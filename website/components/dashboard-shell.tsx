import Link from "next/link";
import { LayoutGrid, ArrowUpRight, ShieldCheck, BookOpen } from "lucide-react";
import { Brand } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-provider";
export function DashboardShell({
  children,
  name,
}: {
  children: React.ReactNode;
  name?: string;
}) {
  return (
    <div className="dashboard">
      <aside className="dashboard-sidebar">
        <Brand />
        <nav className="dashboard-sidebar-nav" aria-label="Панель управления">
          <Link href="/dashboard" className="active">
            <LayoutGrid size={16} /> Мои серверы
          </Link>
          <Link href="/#features">
            <BookOpen size={16} /> Возможности <ArrowUpRight size={13} />
          </Link>
        </nav>
        <div className="dashboard-sidebar-footer">
          <ShieldCheck size={17} />
          <p>
            Только ваши серверы.
            <br />
            Только нужные настройки.
          </p>
          <Link
            href="/privacy"
            className="text-link"
            style={{ marginTop: 15, fontSize: 9 }}
          >
            О ваших данных <ArrowUpRight size={12} />
          </Link>
        </div>
      </aside>
      <div className="dashboard-body">
        <header className="dashboard-topbar">
          <span>ПРОСТРАНСТВО УПРАВЛЕНИЯ</span>
          <div>
            <ThemeToggle />
            {name && (
              <>
                <span>{name}</span>
                <form action="/api/auth/logout" method="post">
                  <button type="submit">Выйти</button>
                </form>
              </>
            )}
          </div>
        </header>
        <main id="main" className="dashboard-main">
          {children}
        </main>
      </div>
    </div>
  );
}
