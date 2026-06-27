import { useCallback, useEffect, useRef, useState } from "react";
import { DropZone } from "../components/DropZone";
import { UploadQueue, type UploadTask } from "../components/UploadQueue";
import { DocumentList } from "../components/DocumentList";
import {
  type Document,
  deleteDocument,
  getDocument,
  listDocuments,
  uploadDocument,
} from "../services/api";

const POLL_INTERVAL_MS = 1500;

export function HomePage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [tasks, setTasks] = useState<UploadTask[]>([]);

  // Track active polling timers so we can clean them up on unmount.
  const timers = useRef<Set<ReturnType<typeof setTimeout>>>(new Set());

  const refreshList = useCallback(async () => {
    setListLoading(true);
    setListError(null);
    try {
      const data = await listDocuments();
      setDocuments(data.documents);
    } catch (err) {
      setListError(err instanceof Error ? err.message : "Не удалось загрузить список");
    } finally {
      setListLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshList();
    const snapshot = timers.current;
    return () => {
      snapshot.forEach((t) => clearTimeout(t));
      snapshot.clear();
    };
  }, [refreshList]);

  const updateTask = useCallback((localId: string, patch: Partial<UploadTask>) => {
    setTasks((prev) =>
      prev.map((t) => (t.localId === localId ? { ...t, ...patch } : t)),
    );
  }, []);

  const pollUntilDone = useCallback(
    (localId: string, documentId: string) => {
      const tick = async () => {
        try {
          const doc = await getDocument(documentId);
          updateTask(localId, {
            status: doc.status,
            errorMessage: doc.error_message,
          });
          if (doc.status === "done" || doc.status === "error") {
            void refreshList();
            return; // stop polling
          }
        } catch {
          // transient error — keep polling
        }
        const timer = setTimeout(tick, POLL_INTERVAL_MS);
        timers.current.add(timer);
      };
      const first = setTimeout(tick, POLL_INTERVAL_MS);
      timers.current.add(first);
    },
    [refreshList, updateTask],
  );

  const handleFiles = useCallback(
    (files: File[]) => {
      files.forEach((file) => {
        const localId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
        const task: UploadTask = {
          localId,
          fileName: file.name,
          progress: 0,
          status: "uploading",
        };
        setTasks((prev) => [task, ...prev]);

        void uploadDocument(file, (fraction) =>
          updateTask(localId, { progress: fraction }),
        )
          .then((accepted) => {
            // Upload accepted; backend now indexing in background.
            updateTask(localId, { status: "indexing", progress: 1 });
            void refreshList();
            pollUntilDone(localId, accepted.id);
          })
          .catch((err) => {
            updateTask(localId, {
              status: "error",
              errorMessage: err instanceof Error ? err.message : "Ошибка загрузки",
            });
          });
      });
    },
    [pollUntilDone, refreshList, updateTask],
  );

  const dismissTask = useCallback((localId: string) => {
    setTasks((prev) => prev.filter((t) => t.localId !== localId));
  }, []);

  const handleDelete = useCallback(
    async (doc: Document) => {
      if (!window.confirm(`Удалить «${doc.file_name}»? Это действие необратимо.`)) return;
      setDeletingId(doc.id);
      try {
        await deleteDocument(doc.id);
        setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
      } catch (err) {
        setListError(err instanceof Error ? err.message : "Не удалось удалить документ");
      } finally {
        setDeletingId(null);
      }
    },
    [],
  );

  const anyActive = documents.some(
    (d) => d.status === "uploading" || d.status === "indexing",
  );

  // While documents are still indexing on the server, keep the list fresh.
  useEffect(() => {
    if (!anyActive) return;
    const timer = setTimeout(() => void refreshList(), POLL_INTERVAL_MS * 2);
    timers.current.add(timer);
    return () => clearTimeout(timer);
  }, [anyActive, documents, refreshList]);

  return (
    <div className="page-grid two-col">
      <section>
        <div className="card card-pad">
          <h2 className="section-title">Загрузка документов</h2>
          <p className="muted" style={{ marginTop: 0 }}>
            Поддерживаются файлы PDF и DOCX, размером до 20&nbsp;МБ.
          </p>
          <DropZone onFiles={handleFiles} />
          <UploadQueue tasks={tasks} onDismiss={dismissTask} />
        </div>
      </section>

      <section>
        <DocumentList
          documents={documents}
          loading={listLoading}
          error={listError}
          deletingId={deletingId}
          onDelete={handleDelete}
          onRefresh={refreshList}
        />
      </section>
    </div>
  );
}
