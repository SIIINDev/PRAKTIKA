# Архитектура системы

Документ описывает компоненты системы, потоки данных (конвейер загрузки и конвейер поиска),
маппинг индекса Elasticsearch и обоснование принятых решений.

---

## 1. Обзор компонентов

Система состоит из шести контейнеров, оркеструемых через Docker Compose.

| Компонент | Контейнер | Технология | Роль |
|-----------|-----------|------------|------|
| Frontend (SPA) | `front` | React 18 + TS, собран Vite, отдаётся Nginx | UI загрузки и поиска; проксирует `/api` на backend |
| Backend (API) | `app` | Python 3.12 + FastAPI (uvicorn) | REST API, валидация, конвейер обработки, поиск |
| Реляционная БД | `postgres` | PostgreSQL 16 | Метаданные документов и история поиска |
| Поисковый движок | `elasticsearch` | Elasticsearch 8.13 | Полнотекстовый индекс `documents` (russian analyzer) |
| Кэш | `redis` | Redis 7 | Кэш результатов поиска (TTL 5 мин) |
| Метрики | `prometheus` | Prometheus | Сбор метрик с `app:8000/metrics` |
| Дашборд | `grafana` | Grafana | Визуализация метрик |

Граница доверия: браузер общается только с `front` (порт 8080). Nginx внутри `front`
проксирует запросы `/api`, `/docs`, `/openapi.json`, `/metrics`, `/health` на `app:8000`.
Хранилища (PostgreSQL, Elasticsearch, Redis) не публикуются наружу и доступны только во
внутренней сети Compose.

### Слои backend

```
app/
  api/        — HTTP-слой: роутеры FastAPI, коды ответов, проверка входных данных
  schemas/    — Pydantic DTO: формы запросов/ответов, валидация формы (response_model)
  services/   — бизнес-логика: extractor, chunker, indexer, es_client, cache, validation
  models/     — ORM-модели SQLAlchemy (таблицы documents, search_history)
  core/       — конфигурация (env), движок БД и сессии, кастомные метрики
  main.py     — фабрика приложения, CORS, подключение роутеров, lifespan
```

Разделение по слоям даёт тестируемость: «чистые» функции (`chunker`, `validation`, `extractor`)
проверяются юнит-тестами без поднятия внешних сервисов.

---

## 2. Модель данных (PostgreSQL)

Файл: `backend/app/models/document.py`. Таблицы создаются на старте приложения
(`init_db` в `backend/app/core/db.py`).

### Таблица `documents`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | String(36), PK | UUID документа |
| `file_name` | String(512) | Исходное имя файла |
| `content_type` | String(128) | MIME-тип |
| `size_bytes` | Integer | Размер загруженного файла |
| `status` | String(32) | `uploading` / `indexing` / `done` / `error` |
| `chunk_count` | Integer | Число проиндексированных чанков |
| `error_message` | Text, nullable | Текст ошибки при `status=error` |
| `stored_path` | String(1024) | Путь к сохранённому файлу на диске (том `uploads_data`) |
| `uploaded_at` | DateTime | Время загрузки (server default `now()`) |
| `indexed_at` | DateTime, nullable | Время завершения индексации |

### Таблица `search_history`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer, PK | Автоинкремент |
| `query` | String(1024) | Текст запроса |
| `results_count` | Integer | Число найденных результатов |
| `created_at` | DateTime | Время запроса |

> PostgreSQL хранит метаданные и историю; полнотекстовое содержимое (чанки) хранится в
> Elasticsearch. Это разделение ответственности: реляционная БД — за состояние и жизненный
> цикл документа, поисковый движок — за индекс и релевантность.

---

## 3. Конвейер загрузки и индексации

Последовательность при `POST /api/v1/documents/upload`
(`backend/app/api/documents.py` → `backend/app/services/indexer.py`):

```
Браузер                Nginx           FastAPI (app)            PostgreSQL    Elasticsearch
   │  multipart file      │                  │                       │             │
   │─────────────────────►│─────────────────►│                       │             │
   │                      │   validate_upload (формат, размер ≤20МБ)  │             │
   │                      │                  │── 400 если невалидно ──┤             │
   │                      │      uuid4(), сохранить файл на диск       │             │
   │                      │                  │── INSERT status=uploading ──────────►│ (нет)
   │  202 {id, status}    │                  │                       │             │
   │◄─────────────────────│◄─────────────────│                       │             │
   │                      │   BackgroundTask: process_document        │             │
   │                      │      status=indexing ─────────────────────►│            │
   │                      │      extract_text (pdfplumber/python-docx) │            │
   │                      │      chunk_text (1000/100)                 │            │
   │                      │      ensure_index + bulk index ───────────────────────►│
   │                      │      status=done, chunk_count, indexed_at ►│            │
```

Этапы:

1. **Приём и валидация** — `validate_upload` проверяет расширение (`pdf`/`docx`), MIME и
   размер (≤ `max_upload_mb`). При нарушении — `HTTP 400` с понятным сообщением.
2. **Сохранение** — генерируется UUID, файл пишется в `UPLOAD_DIR` (том `uploads_data`),
   в БД создаётся строка со статусом `uploading`. Клиенту немедленно возвращается `202`.
3. **Фоновая обработка** (`process_document`) — статус переводится в `indexing`; затем:
   - `extract_text` извлекает текст постранично (PDF: страница за страницей; DOCX: одна
     «страница» №1, включая текст таблиц);
   - `chunk_text` режет текст на чанки 1000 символов с перекрытием 100 (скользящее окно);
   - `index_document` делает bulk-индексацию чанков в ES с `refresh="wait_for"` (поиск
     сразу видит новые данные);
   - статус переводится в `done` с `chunk_count` и `indexed_at`.
4. **Обработка ошибок** — любая ошибка этапа (пустой/битый файл, нет текста) перехватывается,
   статус становится `error` с текстом в `error_message`. Фоновая задача никогда не «падает».

Фронтенд опрашивает `GET /documents/{id}` каждые 1.5 с (`pollUntilDone` в `HomePage.tsx`),
пока статус не станет `done` или `error`, и обновляет прогресс-бар и список.

---

## 4. Конвейер поиска

Последовательность при `GET /api/v1/search?q=...&page=&size=`
(`backend/app/api/search.py` → `backend/app/services/es_client.py`):

```
Браузер          FastAPI (app)            Redis              Elasticsearch     PostgreSQL
   │ GET /search?q  │                        │                     │              │
   │───────────────►│ q.strip(); пусто → 400 │                     │              │
   │                │── GET search:q:page:size ►│                  │              │
   │                │◄── hit? → cached=true ────┤                  │              │
   │   (если miss)  │── multi_match + highlight ──────────────────►│              │
   │                │◄── total, took, hits ───────────────────────┤              │
   │                │── SET search:q:page:size (TTL 300) ►│        │              │
   │                │── INSERT search_history ───────────────────────────────────►│
   │ 200 {results}  │   inc метрик (cached/not, latency)           │              │
   │◄───────────────│                        │                     │              │
```

Этапы:

1. **Валидация запроса** — пустой `q` (после `strip`) → `HTTP 400`. `page ≥ 1`, `size` 1..50.
2. **Кэш** — ключ `search:{q}:{page}:{size}`. При попадании ответ берётся из Redis, в нём
   проставляется `cached: true`. Кэш «мягкий»: при недоступности Redis запрос просто идёт в ES
   (graceful degradation, см. `cache.get_json`/`set_json`).
3. **Поиск в ES** — `multi_match` по полям `text` и `file_name` с подсветкой (`highlight`,
   фрагмент 150 символов, теги `<em>…</em>`). Результаты ранжируются по `_score`.
4. **Постобработка** — формируется ответ `SearchOut` (query, total, page, size, took_ms,
   cached, results[]), кладётся в кэш с TTL 300 с, запрос записывается в `search_history`.
5. **Метрики** — счётчик `kb_search_requests_total{cached}` и гистограмма
   `kb_search_latency_seconds` (`backend/app/core/metrics.py`), плюс стандартные метрики
   HTTP от instrumentator.

Если ES недоступен, поиск возвращает `HTTP 503` («Search backend unavailable»).

---

## 5. Индекс Elasticsearch `documents`

Определён в `backend/app/services/es_client.py` (`INDEX_SETTINGS`), создаётся идемпотентно
(`ensure_index`) на старте приложения и перед первой индексацией.

### Настройки анализа

```json
{
  "settings": {
    "analysis": {
      "analyzer": {
        "russian_custom": { "type": "russian" }
      }
    }
  }
}
```

Встроенный анализатор `russian` выполняет токенизацию, приведение к нижнему регистру,
стоп-слова и стемминг русского языка. Благодаря стеммингу запрос «нейронные сети» находит
формы «нейронных сетей», «нейронной сети» и т. п.

### Маппинг полей

| Поле | Тип | Назначение |
|------|-----|------------|
| `chunk_id` | keyword | Идентификатор чанка `"{doc_id}:{chunk_index}"` (он же `_id` документа ES) |
| `document_id` | keyword | UUID документа-владельца (для удаления чанков `delete_by_query`) |
| `file_name` | text + `.keyword` | Имя файла; участвует в `multi_match`, `.keyword` — для точных совпадений |
| `page_number` | integer | Номер страницы (для отображения «стр. N») |
| `chunk_index` | integer | Порядковый номер чанка в документе |
| `text` | text, analyzer `russian_custom` | Текст чанка — основное поле поиска и подсветки |
| `created_at` | date | Время индексации |

Запрос поиска:

```json
{
  "from": (page-1)*size,
  "size": size,
  "query": { "multi_match": { "query": q, "fields": ["text", "file_name"] } },
  "highlight": {
    "pre_tags": ["<em>"], "post_tags": ["</em>"],
    "fragment_size": 150, "number_of_fragments": 1,
    "fields": { "text": {} }
  }
}
```

---

## 6. Обоснование ключевых решений

- **Elasticsearch для поиска, PostgreSQL для метаданных.** Разделение по ответственности:
  ES даёт стемминг, релевантность и подсветку «из коробки»; реляционная БД — транзакционное
  хранение состояния документов и истории.
- **Чанкинг 1000/100.** Чанк ~1000 символов — компромисс между точностью совпадения
  (мелкие фрагменты) и контекстом для подсветки. Перекрытие 100 символов гарантирует, что
  фраза на границе двух чанков не «разорвётся» и будет найдена.
- **Фоновая индексация + статусы.** Тяжёлый разбор PDF не должен блокировать HTTP-ответ —
  клиент получает `202` мгновенно, а фронтенд показывает прогресс через опрос статуса.
- **Кэш с мягкой деградацией.** Redis ускоряет повторные запросы, но его отказ не ломает
  поиск — система остаётся работоспособной.
- **Безопасная подсветка.** Фрагменты от ES не вставляются как HTML; компонент `Highlight`
  токенизирует только `<em>`/`</em>` и рендерит остальное как текст (React экранирует),
  что исключает XSS из содержимого документов.
- **Идемпотентная инициализация.** `ensure_index` и `init_db` безопасно вызываются повторно,
  а `lifespan` деградирует мягко: если зависимость недоступна на старте, приложение
  поднимается и сообщает об этом в `/health`.
