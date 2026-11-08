"use client";
import Link from "next/link";
import { useState } from "react";
import { Menu, X, ArrowUpRight } from "lucide-react";
import { Brand } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-provider";
export function Header() {
  const [open, setOpen] = useState(false);
  return (
    <header className="header">
      <div className="header-inner">
        <Brand />
        <nav
          className={open ? "main-nav is-open" : "main-nav"}
          aria-label="Основная навигация"
        >
          <Link href="/#features" onClick={() => setOpen(false)}>
            Возможности
          </Link>
          <Link href="/#music" onClick={() => setOpen(false)}>
            Музыка
          </Link>
        </nav>
        <div className="header-actions">
          <ThemeToggle />
          <Link className="header-login" href="/dashboard">
            Панель управления <ArrowUpRight size={15} />
          </Link>
          <button
            className="mobile-menu"
            aria-label={open ? "Закрыть меню" : "Открыть меню"}
            aria-expanded={open}
            onClick={() => setOpen(!open)}
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>
    </header>
  );
}
