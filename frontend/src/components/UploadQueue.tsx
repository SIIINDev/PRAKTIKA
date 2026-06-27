import type { DocumentStatus } from "../services/api";
import { STATUS_LABELS } from "./StatusBadge";

export interface UploadTask {
  localId: string;
  fileName: string;
  /** 0..1 upload progress, only meaningful during "uploading". */
  progress: number;
  status: DocumentStatus;
  errorMessage?: string | null;
}

interface UploadQueueProps {
  tasks: UploadTask[];
  onDismiss: (localId: string) => void;
}

export function UploadQueue({ tasks, onDismiss }: UploadQueueProps) {
  if (tasks.length === 0) return null;

  return (
    <div className="upload-list" aria-live="polite">
      {tasks.map((t) => {
        const pct =
          t.status === "uploading"
            ? Math.round(t.progress * 100)
            : t.status === "done" || t.status === "error"
              ? 100
              : 100;
        const indeterminate = t.status === "indexing";

        return (
          <div className="upload-item" key={t.localId} data-testid="upload-item">
            <div className="upload-item-head">
              <span className="upload-name">{t.fileName}</span>
              <span className={`badge ${t.status}`} data-status={t.status}>
                {t.status === "uploading"
                  ? `${STATUS_LABELS.uploading} ${pct}%`
                  : STATUS_LABELS[t.status]}
              </span>
            </div>

            <div className="progress-track">
              <div
                className={`progress-fill${indeterminate ? " indeterminate" : ""}${
                  t.status === "done" ? " done" : ""
                }${t.status === "error" ? " error" : ""}`}
                style={indeterminate ? undefined : { width: `${pct}%` }}
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={indeterminate ? undefined : pct}
                aria-label={`${t.fileName}: ${STATUS_LABELS[t.status]}`}
              />
            </div>

            {t.status === "error" && t.errorMessage ? (
              <div className="result-sub" style={{ color: "var(--danger)", marginTop: 6 }}>
                {t.errorMessage}
              </div>
            ) : null}

            {(t.status === "done" || t.status === "error") && (
              <button
                type="button"
                className="btn btn-sm"
                style={{ marginTop: 8 }}
                onClick={() => onDismiss(t.localId)}
              >
                Скрыть
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
