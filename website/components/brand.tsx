import Link from "next/link";
export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link href="/" className="brand" aria-label="Discord Bot — главная">
      <span className="brand-symbol" aria-hidden="true">
        <svg viewBox="0 0 40 40" fill="none">
          <ellipse
            cx="20"
            cy="20"
            rx="15"
            ry="7"
            transform="rotate(-42 20 20)"
          />
          <ellipse
            cx="20"
            cy="20"
            rx="15"
            ry="7"
            transform="rotate(42 20 20)"
          />
          <circle cx="20" cy="20" r="3" />
        </svg>
      </span>
      {!compact && (
        <span>
          Discord Bot
        </span>
      )}
    </Link>
  );
}
export function DiscordIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M19.7 5.1a18.6 18.6 0 0 0-4.5-1.4l-.5 1a16.7 16.7 0 0 0-5.4 0l-.5-1a18.6 18.6 0 0 0-4.5 1.4C1.5 9.2.7 13.2 1.1 17.1a18.4 18.4 0 0 0 5.6 2.8l1.1-1.8-1.7-.8.4-.3a13.2 13.2 0 0 0 11 0l.4.3-1.7.8 1.1 1.8a18.4 18.4 0 0 0 5.6-2.8c.5-4.5-.8-8.5-3.2-12ZM8.5 14.8c-1.1 0-1.9-1-1.9-2.2s.8-2.2 1.9-2.2 1.9 1 1.9 2.2-.8 2.2-1.9 2.2Zm7 0c-1.1 0-1.9-1-1.9-2.2s.8-2.2 1.9-2.2 1.9 1 1.9 2.2-.8 2.2-1.9 2.2Z" />
    </svg>
  );
}
