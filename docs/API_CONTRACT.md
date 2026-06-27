# API Contract — Intelligent Knowledge Base Search

Base URL: `/api/v1`. All responses are JSON unless noted. OpenAPI/Swagger UI is served at `/docs`.

This document is the single source of truth shared between Backend (BE) and Frontend (FE). Do not change a shape here without updating both sides.

## Status codes

| Code | Meaning |
|------|---------|
| 200  | OK |
| 202  | Accepted (upload queued for indexing) |
| 400  | Validation error (bad format, too large, empty query) |
| 404  | Resource not found |
| 500  | Internal server error |

Error body shape:

```json
{ "detail": "human readable message" }
```

## Document model

```json
{
  "id": "f8c1e0e2-....-uuid",
  "file_name": "lecture-01.pdf",
  "content_type": "application/pdf",
  "size_bytes": 482113,
  "status": "uploading | indexing | done | error",
  "chunk_count": 42,
  "error_message": null,
  "uploaded_at": "2026-06-28T10:00:00Z",
  "indexed_at": "2026-06-28T10:00:05Z"
}
```

`status` lifecycle: `uploading` → `indexing` → `done` (or `error` with `error_message`). The frontend polls `GET /documents/{id}` (or the list) to render the progress states **Загрузка… / Индексация… / Готово / Ошибка**.

## Endpoints

### POST /api/v1/documents/upload  (BE-01..05, FE-01, FE-02)
Multipart form upload. Field name: `file`. Supports multiple sequential calls for multi-file upload.

- Validates: extension/MIME in `{pdf, docx}`, size ≤ 20 MB. Otherwise `400`.
- Generates a UUID per document (BE-03).
- Persists the Document row with status `uploading`, returns immediately `202`, and runs extraction → chunking (1000 chars / 100 overlap) → ES indexing in a background task.

Response `202`:
```json
{ "id": "uuid", "file_name": "lecture-01.pdf", "status": "uploading" }
```

### GET /api/v1/documents  (FE-03)
List uploaded documents, newest first.
```json
{ "documents": [ Document, ... ], "total": 12 }
```

### GET /api/v1/documents/{id}
Single document. `404` if not found. Used for progress polling.

### DELETE /api/v1/documents/{id}
Deletes the document row, its file, and all its ES chunks. `204` on success, `404` if missing.

### GET /api/v1/search  (BE-08, BE-09, BE-10, FE-04..08)
Query params:
- `q` (string, required, non-empty — empty → `400`)
- `page` (int, default 1, 1-based)
- `size` (int, default 10, max 50)

Executes an Elasticsearch `multi_match` over `text` (and `file_name`) with the Russian analyzer, highlighting, and pagination. Frequent identical `(q,page,size)` queries are served from Redis (TTL 300 s, BE-10). Each search is recorded in history.

Response `200`:
```json
{
  "query": "нейронные сети",
  "total": 37,
  "page": 1,
  "size": 10,
  "took_ms": 12,
  "cached": false,
  "results": [
    {
      "chunk_id": "uuid#3",
      "document_id": "uuid",
      "file_name": "lecture-01.pdf",
      "page": 4,
      "text": "полный текст чанка ...",
      "highlight": "... <em>нейронные</em> <em>сети</em> ...",
      "score": 8.42
    }
  ]
}
```
The `highlight` field contains ES `<em>`-wrapped fragments; the frontend renders matches with a yellow background (FE-06). When `results` is empty the frontend shows the FE-08 message.

### GET /api/v1/search/history
Recent distinct search queries, newest first.
```json
{ "history": [ { "query": "нейронные сети", "results_count": 37, "created_at": "..." } ] }
```

### GET /health
Liveness + dependency status.
```json
{ "status": "ok", "elasticsearch": "up", "redis": "up", "postgres": "up" }
```

### GET /metrics
Prometheus exposition format (request counts, latency histograms). Includes a counter for `/search` calls and a latency histogram (DO-06).

## Elasticsearch index `documents`

Analyzer: `russian`. Mapping:
- `chunk_id` keyword
- `document_id` keyword
- `file_name` text + `.keyword`
- `page_number` integer
- `chunk_index` integer
- `text` text, analyzer `russian`
- `created_at` date
