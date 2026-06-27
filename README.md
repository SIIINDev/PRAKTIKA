# Интеллектуальная поисковая система по внутренней базе знаний университета

> Учебная практика, направление 09.03.04 «Программная инженерия».
> Команда из 4 человек: Backend (BE), Frontend (FE), DevOps (DO), QA.

`Python 3.12` · `FastAPI` · `React 18 + TypeScript` · `PostgreSQL 16` · `Elasticsearch 8.13` · `Redis 7` · `Docker Compose` · `GitHub Actions` · `Prometheus + Grafana`

Веб-приложение, которое позволяет загрузить документы (PDF / DOCX), автоматически извлечь
из них текст, разбить его на чанки, проиндексировать в Elasticsearch с русскоязычным
анализатором и выполнять по ним полнотекстовый поиск с ранжированием, подсветкой
совпадений и кэшированием частых запросов.

---

## Возможности

- **Загрузка документов** — drag-and-drop, множественная загрузка, форматы PDF и DOCX,
  ограничение размера 20 МБ, серверная валидация формата и размера (HTTP 400 при ошибке).
- **Конвейер обработки** — извлечение текста (`pdfplumber` для PDF, `python-docx` для DOCX) →
  разбиение на чанки по 1000 символов с перекрытием 100 → индексация в Elasticsearch.
- **Статусы обработки** — `Загрузка… → Индексация… → Готово` (или `Ошибка` с сообщением),
  прогресс-бар и опрос статуса с фронтенда.
- **Полнотекстовый поиск** — `multi_match` по полям `text` и `file_name`, ранжирование по
  релевантности (`score`), подсветка совпадений (`<em>` → жёлтый фон), пагинация по 10.
- **Кэширование** — повторные идентичные запросы отдаются из Redis (TTL 5 минут),
  в ответе проставляется флаг `cached`.
- **История запросов** — последние запросы сохраняются и показываются как быстрые «чипы».
- **Адаптивный интерфейс** — корректная вёрстка от 320px до 1920px, доступность (axe-core: 0 нарушений).
- **Наблюдаемость** — метрики Prometheus (`/metrics`), дашборд Grafana, healthcheck `/health`.

---

## Архитектура (общая схема)

```
                            ┌──────────────────────────────────────────────┐
   Браузер                  │                Docker Compose                  │
 ┌──────────┐   HTTP :8080  │  ┌───────────┐      /api      ┌─────────────┐  │
 │  React   │ ─────────────►│  │   front   │ ─────────────► │     app     │  │
 │   SPA    │ ◄─────────────│  │  (nginx)  │  proxy_pass    │  (FastAPI)  │  │
 └──────────┘               │  └───────────┘                └──────┬──────┘  │
                            │                                      │         │
                            │     ┌────────────────┬──────────────┼───────┐ │
                            │     ▼                ▼              ▼ │       │ │
                            │ ┌─────────┐   ┌─────────────┐  ┌────────┐    │ │
                            │ │PostgreSQL│  │Elasticsearch│  │ Redis  │    │ │
                            │ │ метадан- │  │  индекс     │  │ кэш    │    │ │
                            │ │  ные     │  │ documents   │  │ поиска │    │ │
                            │ └─────────┘   └─────────────┘  └────────┘    │ │
                            │                                              │ │
                            │  ┌────────────┐   scrape /metrics  ┌───────┐ │ │
                            │  │ Prometheus │ ◄──────────────────┤  app  │ │ │
                            │  └─────┬──────┘                    └───────┘ │ │
                            │        │ datasource                          │ │
                            │  ┌─────▼──────┐                              │ │
                            │  │  Grafana   │  дашборд KB Search           │ │
                            │  └────────────┘                              │ │
                            └──────────────────────────────────────────────┘
```

Подробное описание компонентов и потоков данных — в [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Технологический стек

| Слой | Технология | Версия | Назначение |
|------|------------|--------|------------|
| Backend | Python | 3.12 | Язык backend |
| Backend | FastAPI | 0.115 | REST API, OpenAPI/Swagger, фоновые задачи |
| Backend | SQLAlchemy (async) + asyncpg | 2.0 / 0.30 | ORM и драйвер PostgreSQL |
| Backend | pdfplumber | 0.11 | Извлечение текста из PDF |
| Backend | python-docx | 1.1 | Извлечение текста из DOCX |
| Backend | elasticsearch (async) | 8.16 (клиент) | Индексация и поиск |
| Backend | redis (async) | 5.2 | Кэш частых запросов |
| Backend | prometheus-fastapi-instrumentator | 7.0 | Метрики `/metrics` |
| Frontend | React + TypeScript | 18.3 / 5.6 | SPA |
| Frontend | Vite | 5.4 | Сборка и dev-сервер |
| Хранилища | PostgreSQL | 16 | Метаданные документов и история поиска |
| Хранилища | Elasticsearch | 8.13 | Полнотекстовый индекс (russian analyzer) |
| Хранилища | Redis | 7 | Кэш результатов поиска |
| Инфра | Docker / Docker Compose | — | Контейнеризация и оркестрация локально |
| Инфра | Nginx | alpine | Отдача статики SPA + проксирование `/api` |
| CI/CD | GitHub Actions | — | Линт, тесты, сборка образов |
| Мониторинг | Prometheus + Grafana | latest | Сбор и визуализация метрик |
| Тесты | pytest + coverage | — | Юнит-тесты backend |
| Тесты | Playwright | 1.48 | E2E-сценарии |
| Тесты | Locust | — | Нагрузочное тестирование |

---

## Быстрый старт

Требуется установленный Docker и Docker Compose.

```bash
# 1. Создать .env из примера (при необходимости поменять порты / пароли)
cp .env.example .env

# 2. Собрать и запустить весь стек одной командой
docker compose up --build

# 3. (опционально) Загрузить 10 тестовых PDF-лекций из открытого доступа
./init.sh                       # или: API_URL=http://localhost:8000 ./init.sh
```

После запуска доступны:

| Сервис | URL | Описание |
|--------|-----|----------|
| Веб-интерфейс | http://localhost:8080 | Главное приложение (загрузка + поиск) |
| Swagger UI | http://localhost:8000/docs | Интерактивная документация API |
| OpenAPI JSON | http://localhost:8000/openapi.json | Схема OpenAPI 3.0 |
| Healthcheck | http://localhost:8000/health | Статус зависимостей |
| Метрики | http://localhost:8000/metrics | Экспозиция Prometheus |
| Prometheus | http://localhost:9090 | Сбор метрик |
| Grafana | http://localhost:3000 | Дашборд «KB Search — API Metrics» (admin / admin) |

> Все порты настраиваются через `.env` (`APP_PORT`, `FRONT_PORT`, `PROMETHEUS_PORT`,
> `GRAFANA_PORT`). Если порт занят — измените значение в `.env` и перезапустите `docker compose up`.

Проверка готовности стека:

```bash
curl -s http://localhost:8000/health
# {"status":"ok","elasticsearch":"up","redis":"up","postgres":"up"}
```

---

## Структура репозитория

```
.
├── backend/                      # Python + FastAPI backend
│   ├── app/
│   │   ├── api/                  # HTTP-эндпоинты (documents, search, health)
│   │   ├── core/                 # Конфигурация, БД, метрики
│   │   ├── models/               # SQLAlchemy-модели (Document, SearchHistory)
│   │   ├── schemas/              # Pydantic DTO (document, search, health)
│   │   ├── services/             # Бизнес-логика (extractor, chunker, indexer,
│   │   │                         #   es_client, cache, validation)
│   │   └── main.py               # Точка входа (фабрика приложения, lifespan)
│   ├── tests/unit/               # Юнит-тесты (pytest)
│   ├── requirements.txt
│   ├── pyproject.toml            # Конфиг ruff и pytest/coverage
│   └── Dockerfile
├── frontend/                     # React + TypeScript (Vite)
│   ├── src/
│   │   ├── components/           # DropZone, ResultCard, Highlight, Pagination, …
│   │   ├── pages/                # HomePage (документы), SearchPage (поиск)
│   │   ├── services/api.ts       # Клиент REST API
│   │   ├── utils/                # Форматирование
│   │   └── App.tsx               # Корневой компонент + навигация
│   ├── package.json
│   └── Dockerfile                # Multi-stage: vite build → nginx
├── deploy/
│   ├── nginx/nginx.conf          # Отдача SPA + проксирование /api, /docs, /metrics
│   ├── prometheus/prometheus.yml # Конфиг сбора метрик
│   └── grafana/provisioning/     # Datasource Prometheus + дашборд
├── tests/
│   ├── fixtures/                 # Тестовые документы (QA-03)
│   ├── e2e/                      # Playwright (QA-02)
│   ├── load/                     # Locust (QA-04)
│   └── precision/                # Precision@3 (QA-05)
├── docs/                         # Документация (см. ниже)
├── scripts/make_fixtures.py      # Генерация тестовых фикстур
├── docker-compose.yml
├── .env.example
├── .github/workflows/ci.yml
├── init.sh                       # Сидирование БЗ 10 PDF-лекциями (DO-07)
└── README.md
```

---

## Запуск тестов

### Backend — юнит-тесты (QA-01)

```bash
cd backend
pip install -r requirements-dev.txt
ruff check .          # линтер (PEP 8 и пр.)
pytest                # 25 тестов, покрытие выводится в терминал (--cov)
```

Текущее состояние: 25 тестов проходят, покрытие 62% (цель >50% выполнена), ruff без замечаний.

### Frontend — типизация и сборка

```bash
cd frontend
npm ci
npm run typecheck     # tsc --noEmit
npm run build         # сборка production-бандла Vite
```

### E2E — Playwright (QA-02)

Требует запущенного стека (`docker compose up`).

```bash
cd tests/e2e
npm ci
npx playwright install --with-deps chromium
npm test              # сценарий: загрузка → индексация → поиск → подсветка → пустая выдача
```

Результаты фиксируются в `tests/e2e/REPORT.md`.

### Нагрузочное тестирование — Locust (QA-04)

```bash
cd tests/load
# запуск 50 одновременных пользователей по /search; отчёт о времени отклика
```

Результаты фиксируются в `tests/load/REPORT.md`.

### Качество поиска — Precision@3 (QA-05)

```bash
cd tests/precision
# 10 эталонных запросов, проверка попадания нужного документа в топ-3
```

Результаты фиксируются в `tests/precision/REPORT.md`.

---

## Документация

| Документ | Назначение |
|----------|------------|
| [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) | Контракт REST API (общий для BE и FE) |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Архитектура, потоки данных, маппинг индекса ES |
| [`docs/REQUIREMENTS_TRACEABILITY.md`](docs/REQUIREMENTS_TRACEABILITY.md) | Трассировка всех требований (BE/FE/DO/QA) |
| [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) | Руководство пользователя (QA-06) |
| [`docs/roles/BE.md`](docs/roles/BE.md) | Защита роли Backend-инженера |
| [`docs/roles/FE.md`](docs/roles/FE.md) | Защита роли Frontend-инженера |
| [`docs/roles/DO.md`](docs/roles/DO.md) | Защита роли DevOps-инженера |
| [`docs/roles/QA.md`](docs/roles/QA.md) | Защита роли QA-инженера |
| [`docs/ДНЕВНИК_ПРАКТИКИ.md`](docs/ДНЕВНИК_ПРАКТИКИ.md) | Дневник практики (12 дней) |
| [`docs/ПРЕЗЕНТАЦИЯ.md`](docs/ПРЕЗЕНТАЦИЯ.md) | План защитной презентации |

---

## Лицензия и назначение

Проект учебный, выполнен в рамках учебной практики (23 июня 2026 — 06 июля 2026).
