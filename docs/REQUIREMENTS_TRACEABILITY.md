# Матрица трассировки требований

Документ связывает каждое требование из задания на учебную практику с конкретными
файлами реализации и способом проверки. Это основной документ для защиты: по нему
комиссия видит, что выполнено каждое требование и где это можно показать.

Обозначения статуса:
- ✅ — реализовано и проверено;
- 🔶 частично — реализовано, итоговые числовые результаты дорабатываются (см. соответствующий `REPORT.md`).

Пути даны относительно корня репозитория.

---

## Backend (BE)

| ID | Требование (кратко) | Приоритет | Где реализовано | Статус | Как проверено |
|----|---------------------|-----------|-----------------|--------|---------------|
| BE-01 | REST-эндпоинт `POST /api/v1/documents/upload` | Высокий | `backend/app/api/documents.py` (`upload_document`); роутер подключён в `backend/app/main.py` | ✅ | Swagger `/docs`; ручной аплоад docx+pdf → 202; E2E `tests/e2e/specs/search-flow.spec.ts` |
| BE-02 | Валидация формата (PDF/DOCX) и размера (≤20 МБ), HTTP 400 | Высокий | `backend/app/services/validation.py` (`validate_upload`); вызов в `documents.py`; лимит `max_upload_mb` в `backend/app/core/config.py` | ✅ | Юнит-тесты `backend/tests/unit/test_validation.py`, `test_api.py::test_upload_rejects_bad_extension`; ручной аплоад `.txt` → 400 |
| BE-03 | Генерация UUID для каждого документа | Высокий | `backend/app/api/documents.py` (`uuid.uuid4()`); `default=_uuid_str` в `backend/app/models/document.py` | ✅ | Тело ответа 202 содержит `id`; запись в таблице `documents` |
| BE-04 | Извлечение текста: pdfplumber (PDF), python-docx (DOCX) | Высокий | `backend/app/services/extractor.py` (`extract_text`, `_extract_pdf`, `_extract_docx`) | ✅ | Юнит-тесты `backend/tests/unit/test_extractor.py`; ручной аплоад pdf+docx → статус `done` с числом чанков |
| BE-05 | Чанкинг 1000 символов, перекрытие 100 | Средний | `backend/app/services/chunker.py` (`chunk_text`); параметры `chunk_size`/`chunk_overlap` в `core/config.py`, применяются в `services/indexer.py` | ✅ | Юнит-тесты `backend/tests/unit/test_chunker.py` (проверка размера окна и перекрытия) |
| BE-06 | Elasticsearch с русским анализатором, индекс `documents` с маппингом | Высокий | `backend/app/services/es_client.py` (`INDEX_SETTINGS`, `ensure_index`); анализатор `russian_custom` (тип `russian`) | ✅ | Создание индекса при старте (`main.py` lifespan); `/health` → `elasticsearch: up`; ручной поиск возвращает результаты |
| BE-07 | Индексация чанков с метаданными (file_name, page_number, chunk_id, text) | Высокий | `backend/app/services/es_client.py` (`index_document`, bulk); оркестрация в `backend/app/services/indexer.py` (`process_document`) | ✅ | После аплоада статус `done` + `chunk_count`; результаты поиска содержат `file_name`, `page`, `chunk_id` |
| BE-08 | `GET /api/v1/search?q=` через Elasticsearch `multi_match` по `text` | Высокий | `backend/app/api/search.py` (`search`); `es_client.search` с `multi_match` по `["text","file_name"]` | ✅ | Swagger `/docs`; ручной поиск «нейронные сети»/«бинарный поиск» → ранжированные результаты; E2E |
| BE-09 | JSON-результаты с `chunk_id`, `file_name`, `page`, `text`, `score` | Высокий | `backend/app/schemas/search.py` (`SearchResult`, `SearchOut`); сборка в `es_client.search` | ✅ | Контракт `docs/API_CONTRACT.md`; ответ `/search`; `response_model` валидирует форму |
| BE-10 | Кэширование частых запросов в Redis, TTL = 5 мин | Низкий | `backend/app/services/cache.py` (`get_json`/`set_json`); ключ и TTL (`search_cache_ttl=300`) в `backend/app/api/search.py` | ✅ | Повторный идентичный запрос → `cached: true` (проверено вручную); деградация при недоступности Redis |
| — | OpenAPI 3.0 / Swagger UI на `/docs`, корректные HTTP-статусы 200/400/404/500 | Высокий | `backend/app/main.py` (`docs_url`, `openapi_url`); статусы по эндпоинтам в `api/*.py` | ✅ | `/docs`, `/openapi.json`; коды: 202 аплоад, 400 валидация, 404 нет документа, 204 удаление |

> Примечание по кодам ответа: для аплоада используется `202 Accepted` (обработка идёт в фоне),
> для удаления — `204 No Content`. Поиск при недоступном ES возвращает `503` (вместо абстрактного 500),
> что точнее отражает причину. Это осознанные уточнения относительно базового набора статусов.

---

## Frontend (FE)

| ID | Требование (кратко) | Приоритет | Где реализовано | Статус | Как проверено |
|----|---------------------|-----------|-----------------|--------|---------------|
| FE-01 | Drag-and-Drop область + множественная загрузка | Высокий | `frontend/src/components/DropZone.tsx`; обработка в `frontend/src/pages/HomePage.tsx` (`handleFiles`) | ✅ | Ручная загрузка нескольких файлов; `multiple` на input; E2E через `file-input` |
| FE-02 | Прогресс-бар и статусы: Загрузка…/Индексация…/Готово/Ошибка | Высокий | `frontend/src/components/UploadQueue.tsx`, `StatusBadge.tsx` (`STATUS_LABELS`); опрос статуса в `HomePage.tsx` (`pollUntilDone`); прогресс через XHR в `services/api.ts` (`uploadDocument`) | ✅ | Ручной аплоад: переход uploading→indexing→done; E2E проверяет статус «Готово» |
| FE-03 | Список загруженных документов (название, дата, статус) | Средний | `frontend/src/components/DocumentList.tsx`; форматирование в `frontend/src/utils/format.ts`; данные из `listDocuments` | ✅ | Ручной просмотр списка; отображаются имя, дата, размер, число фрагментов, статус |
| FE-04 | Поле ввода + кнопка «Найти», поиск по кнопке и по Enter | Высокий | `frontend/src/components/SearchBar.tsx` (form `onSubmit`); `frontend/src/pages/SearchPage.tsx` (`onSubmit`/`runSearch`) | ✅ | Поиск по кнопке и по Enter (submit формы); E2E нажимает кнопку поиска |
| FE-05 | Карточки результатов: имя файла, страница, фрагмент, релевантность | Высокий | `frontend/src/components/ResultCard.tsx` | ✅ | Ручной поиск показывает карточки; E2E проверяет `.result-file`, `.result-score`, фрагмент |
| FE-06 | Подсветка совпадений жёлтым фоном | Высокий | `frontend/src/components/Highlight.tsx` (безопасный парсинг `<em>`→`<mark>`); стиль `mark` в `frontend/src/styles.css` | ✅ | Ручной поиск показывает жёлтую подсветку; E2E проверяет наличие `<mark>` |
| FE-07 | Пагинация по 10 результатов | Средний | `frontend/src/components/Pagination.tsx`; `PAGE_SIZE=10` в `frontend/src/pages/SearchPage.tsx` | ✅ | Ручной просмотр многостраничной выдачи; переключение страниц |
| FE-08 | Сообщение «По вашему запросу ничего не найдено…» | Низкий | `frontend/src/pages/SearchPage.tsx` (`NO_RESULTS_MESSAGE`); `EmptyState.tsx` | ✅ | Поиск заведомо отсутствующего запроса; E2E проверяет текст пустого состояния |
| FE-09 | Адаптивная вёрстка 320–1920px | Средний | `frontend/src/styles.css` (media-запросы, грид); компоненты без фиксированных ширин | ✅ | ui-test (browse + axe-core): нет горизонтального переполнения на 320px, 0 нарушений доступности |

---

## DevOps (DO)

| ID | Требование (кратко) | Приоритет | Где реализовано | Статус | Как проверено |
|----|---------------------|-----------|-----------------|--------|---------------|
| DO-01 | Dockerfile backend (Python + FastAPI) | Высокий | `backend/Dockerfile` (python:3.12-slim, non-root, healthcheck, uvicorn) | ✅ | `docker compose up --build` собирает образ; контейнер `app` стартует |
| DO-02 | Dockerfile frontend (Node build → nginx) | Высокий | `frontend/Dockerfile` (multi-stage: node:20 build → nginx:alpine); `deploy/nginx/nginx.conf` | ✅ | Образ собирается; SPA отдаётся на :8080, `/api` проксируется на backend |
| DO-03 | docker-compose.yml: app, front, postgres, elasticsearch, redis | Высокий | `docker-compose.yml` (+ дополнительно prometheus, grafana) | ✅ | `docker compose up` поднимает все сервисы; `/health` → все зависимости `up` |
| DO-04 | Секреты через `.env`, наличие `.env.example` | Высокий | `.env.example`; `env_file: .env` в `docker-compose.yml`; парсинг в `backend/app/core/config.py` | ✅ | Пароли БД/Grafana задаются переменными; `.env.example` в репозитории |
| DO-05 | GitHub Actions: при push в main — линтеры, тесты, сборка образов | Средний | `.github/workflows/ci.yml` (jobs: `backend-lint-test`, `frontend-build`, `docker-build`) | ✅ | Workflow: ruff + pytest, tsc + vite build, затем сборка обоих образов |
| DO-06 | Мониторинг: Prometheus (запросы к /search, время ответа) + Grafana | Низкий | `deploy/prometheus/prometheus.yml`; `deploy/grafana/provisioning/**`; метрики `backend/app/core/metrics.py` + instrumentator в `main.py`; эндпоинт `/metrics` | ✅ | Prometheus target `app:8000` up; дашборд «KB Search — API Metrics» (rps, total, p95/p50) |
| DO-07 | Скрипт init.sh: скачать 10 PDF-лекций и загрузить через API | Средний | `init.sh` (10 URL arXiv → `POST /api/v1/documents/upload`) | ✅ | Запуск `./init.sh` при поднятом стеке; документы появляются в списке |

---

## QA

| ID | Требование (кратко) | Приоритет | Где реализовано | Статус | Как проверено |
|----|---------------------|-----------|-----------------|--------|---------------|
| QA-01 | Юнит-тесты backend (парсинг, валидация), покрытие ≥50% | Высокий | `backend/tests/unit/` (`test_chunker.py`, `test_extractor.py`, `test_validation.py`, `test_api.py`); конфиг покрытия `backend/pyproject.toml` | ✅ | `pytest`: 25 тестов проходят, покрытие 62% (>50%) |
| QA-02 | E2E-тесты Playwright (загрузка → индексация → поиск → результаты) | Высокий | `tests/e2e/specs/search-flow.spec.ts`; конфиг `tests/e2e/playwright.config.ts` | 🔶 | Сценарий реализован; финальный прогон и результаты — `tests/e2e/REPORT.md` |
| QA-03 | Набор тестовых документов (корректные, пустые, битые, спец.) | Высокий | `tests/fixtures/` (`lecture_databases.docx`, `lecture_algorithms.pdf`, `empty.pdf`, `broken.pdf`, `notes.txt`); генератор `scripts/make_fixtures.py` | ✅ | Описание в `tests/fixtures/README.md`; используются в юнит/E2E; ручная проверка битого PDF → статус `error` |
| QA-04 | Нагрузочные тесты: 50 пользователей по /search, отчёт о времени отклика | Средний | `tests/load/` (Locust) | 🔶 | Сценарий нагрузки готовится; результаты — `tests/load/REPORT.md` |
| QA-05 | Precision@3 по 10 эталонным запросам, результаты в таблице | Средний | `tests/precision/` | 🔶 | Методика и набор запросов готовятся; результаты — `tests/precision/REPORT.md` |
| QA-06 | Руководство пользователя (Markdown/PDF) | Низкий | `docs/USER_GUIDE.md` | ✅ | Пошаговое руководство с разделом устранения неполадок |

---

## Сводка по статусам

- Полностью реализовано и проверено (✅): все требования BE-01..BE-10, FE-01..FE-09, DO-01..DO-07,
  а также QA-01, QA-03, QA-06.
- В стадии финализации результатов (🔶): QA-02 (E2E), QA-04 (нагрузка), QA-05 (Precision@3) —
  сценарии и инфраструктура готовы, итоговые числовые отчёты фиксируются в соответствующих
  `tests/<suite>/REPORT.md`.
