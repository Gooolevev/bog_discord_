"use client";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { RefreshCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
export function RefreshButton({
  label = "Проверить снова",
}: {
  label?: string;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  return (
    <Button
      type="button"
      variant="outline"
      disabled={pending}
      onClick={() => startTransition(() => router.refresh())}
    >
      <RefreshCcw size={14} className={pending ? "animate-spin" : ""} />
      {pending ? "Проверяем…" : label}
    </Button>
  );
}
