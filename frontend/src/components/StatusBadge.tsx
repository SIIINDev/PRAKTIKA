import type { DocumentStatus } from "../services/api";

export const STATUS_LABELS: Record<DocumentStatus, string> = {
  uploading: "Загрузка...",
  indexing: "Индексация...",
  done: "Готово",
  error: "Ошибка",
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span className={`badge ${status}`} data-status={status}>
      <span className="badge-dot" aria-hidden="true" />
      {STATUS_LABELS[status]}
    </span>
  );
}
