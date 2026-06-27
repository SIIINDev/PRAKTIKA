export type DocumentStatus = "uploading" | "indexing" | "done" | "error";

export interface Document {
  id: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  status: DocumentStatus;
  chunk_count: number;
  error_message: string | null;
  uploaded_at: string;
  indexed_at: string | null;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
}

export interface UploadAcceptedResponse {
  id: string;
  file_name: string;
  status: DocumentStatus;
}

export interface SearchResultItem {
  chunk_id: string;
  document_id: string;
  file_name: string;
  page: number;
  text: string;
  highlight: string;
  score: number;
}

export interface SearchResponse {
  query: string;
  total: number;
  page: number;
  size: number;
  took_ms: number;
  cached: boolean;
  results: SearchResultItem[];
}

export interface SearchHistoryItem {
  query: string;
  results_count: number;
  created_at: string;
}

export interface SearchHistoryResponse {
  history: SearchHistoryItem[];
}

const API_BASE: string = import.meta.env.VITE_API_BASE ?? "/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseError(res: Response): Promise<never> {
  let detail = `Ошибка запроса (${res.status})`;
  try {
    const body = await res.json();
    if (body && typeof body.detail === "string") detail = body.detail;
  } catch {
    /* response had no JSON body */
  }
  throw new ApiError(detail, res.status);
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { signal });
  if (!res.ok) return parseError(res);
  return (await res.json()) as T;
}

export function listDocuments(signal?: AbortSignal): Promise<DocumentListResponse> {
  return getJson<DocumentListResponse>("/documents", signal);
}

export function getDocument(id: string, signal?: AbortSignal): Promise<Document> {
  return getJson<Document>(`/documents/${encodeURIComponent(id)}`, signal);
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
  if (!res.ok && res.status !== 204) await parseError(res);
}

export function search(
  q: string,
  page: number,
  size: number,
  signal?: AbortSignal,
): Promise<SearchResponse> {
  const params = new URLSearchParams({
    q,
    page: String(page),
    size: String(size),
  });
  return getJson<SearchResponse>(`/search?${params.toString()}`, signal);
}

export function getSearchHistory(signal?: AbortSignal): Promise<SearchHistoryResponse> {
  return getJson<SearchHistoryResponse>("/search/history", signal);
}

/**
 * Upload a single file using XMLHttpRequest so we can report real upload
 * progress (0..1) for the "Загрузка..." state. Resolves with the 202 body.
 */
export function uploadDocument(
  file: File,
  onProgress?: (fraction: number) => void,
): Promise<UploadAcceptedResponse> {
  return new Promise<UploadAcceptedResponse>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    form.append("file", file);

    xhr.open("POST", `${API_BASE}/documents/upload`);

    xhr.upload.onprogress = (event) => {
      if (onProgress && event.lengthComputable) {
        onProgress(event.loaded / event.total);
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        if (onProgress) onProgress(1);
        try {
          resolve(JSON.parse(xhr.responseText) as UploadAcceptedResponse);
        } catch {
          reject(new ApiError("Некорректный ответ сервера", xhr.status));
        }
      } else {
        let detail = `Ошибка загрузки (${xhr.status})`;
        try {
          const body = JSON.parse(xhr.responseText);
          if (body && typeof body.detail === "string") detail = body.detail;
        } catch {
          /* no JSON body */
        }
        reject(new ApiError(detail, xhr.status));
      }
    };

    xhr.onerror = () => reject(new ApiError("Сетевая ошибка при загрузке", 0));
    xhr.send(form);
  });
}
