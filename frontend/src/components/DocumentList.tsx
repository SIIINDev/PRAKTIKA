import type { Document } from "../services/api";
import { StatusBadge } from "./StatusBadge";
import { EmptyState } from "./EmptyState";
import { formatBytes, formatDate } from "../utils/format";

interface DocumentListProps {
  documents: Document[];
  loading: boolean;
  error?: string | null;
  deletingId?: string | null;
  onDelete: (doc: Document) => void;
  onRefresh: () => void;
}

export function DocumentList({
  documents,
  loading,
  error,
  deletingId,
  onDelete,
  onRefresh,
}: DocumentListProps) {
  return (
    <div className="card card-pad">
      <div className="row-between" style={{ marginBottom: 12 }}>
        <h2 className="section-title" style={{ margin: 0 }}>
          Загруженные документы
        </h2>
        <button type="button" className="btn btn-sm" onClick={onRefresh} disabled={loading}>
          Обновить
        </button>
      </div>

      {error ? (
        <div className="error-banner" role="alert">
          {error}
        </div>
      ) : null}

      {loading && documents.length === 0 ? (
        <div className="state">
          <span className="spinner" aria-hidden="true" />
          <div style={{ marginTop: 10 }}>Загрузка списка…</div>
        </div>
      ) : documents.length === 0 ? (
        <EmptyState
          icon="📂"
          title="Пока нет документов"
          message="Загрузите PDF или DOCX, чтобы начать поиск."
        />
      ) : (
        <div className="doc-list" data-testid="doc-list">
          {documents.map((doc) => (
            <div className="doc-item" key={doc.id} data-testid="doc-list-item">
              <div className="doc-main">
                <div className="doc-name">{doc.file_name}</div>
                <div className="doc-meta">
                  {formatDate(doc.uploaded_at)} · {formatBytes(doc.size_bytes)}
                  {doc.status === "done" && doc.chunk_count > 0
                    ? ` · ${doc.chunk_count} фрагм.`
                    : ""}
                  {doc.status === "error" && doc.error_message
                    ? ` · ${doc.error_message}`
                    : ""}
                </div>
              </div>
              <StatusBadge status={doc.status} />
              <button
                type="button"
                className="btn btn-sm btn-danger"
                aria-label={`Удалить ${doc.file_name}`}
                disabled={deletingId === doc.id}
                onClick={() => onDelete(doc)}
              >
                {deletingId === doc.id ? "Удаление…" : "Удалить"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
