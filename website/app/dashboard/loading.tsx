export default function Loading() {
  return (
    <div
      role="status"
      aria-label="Загружаем ваши серверы"
      className="panel-card loading-lines"
    >
      <span className="skeleton" />
      <span className="skeleton" />
      <span className="skeleton" style={{ width: "70%" }} />
      <span className="sr-only">Загружаем ваши серверы…</span>
    </div>
  );
}
