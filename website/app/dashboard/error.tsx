"use client";
import { Button } from "@/components/ui/button";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <div className="panel-card panel-empty">
      <h2>Кажется, связь прервалась.</h2>
      <p>Не удалось открыть панель. Попробуйте ещё раз.</p>
      <Button onClick={reset} style={{ marginTop: 25 }}>
        Попробовать снова
      </Button>
    </div>
  );
}
