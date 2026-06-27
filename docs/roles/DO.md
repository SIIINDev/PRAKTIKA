# Защита роли: DevOps-инженер (DO)

Документ для подготовки к защите своей части проекта.

---

## Моя зона ответственности

> Контейнеризация, настройка CI/CD, мониторинг, управление окружением.

Я отвечал за упаковку приложений в Docker-образы, оркестрацию всего стека через Docker Compose,
конфигурацию через переменные окружения, пайплайн CI/CD на GitHub Actions, мониторинг
(Prometheus + Grafana) и скрипт инициализации базы знаний.

---

## Что я реализовал

| Требование | Что сделано | Файлы |
|------------|-------------|-------|
| DO-01 | Dockerfile backend (python:3.12-slim, non-root, healthcheck, uvicorn) | `backend/Dockerfile` |
| DO-02 | Dockerfile frontend (multi-stage: node build → nginx) + конфиг nginx | `frontend/Dockerfile`, `deploy/nginx/nginx.conf` |
| DO-03 | docker-compose.yml: app, front, postgres, elasticsearch, redis (+ prometheus, grafana) | `docker-compose.yml` |
| DO-04 | Секреты через `.env`, наличие `.env.example`, настраиваемые порты | `.env.example`, `docker-compose.yml`, `backend/app/core/config.py` |
| DO-05 | GitHub Actions: линт + тесты + сборка образов при push в main | `.github/workflows/ci.yml` |
| DO-06 | Мониторинг: Prometheus (метрики /search, время ответа) + Grafana-дашборд | `deploy/prometheus/prometheus.yml`, `deploy/grafana/provisioning/**` |
| DO-07 | init.sh: скачивание 10 PDF-лекций и загрузка через API | `init.sh` |

---

## Ключевые технические решения

- **Healthcheck + `depends_on: condition: service_healthy`.** Каждый сервис данных
  (postgres, elasticsearch, redis) имеет healthcheck; контейнер `app` запускается только после
  того, как все зависимости стали healthy. Это решает классическую проблему «приложение
  поднялось раньше БД».
- **Multi-stage сборка фронтенда.** Стадия 1 (node:20-alpine) собирает Vite-бандл; стадия 2
  (nginx:alpine) отдаёт только статику. Итоговый образ маленький и без Node в рантайме.
- **Nginx как точка входа.** SPA отдаётся на порту 80; запросы `/api`, `/docs`, `/metrics`,
  `/health` проксируются на `app:8000`. Браузер общается с одним origin — нет проблем с CORS.
- **Конфигурация только через переменные окружения.** Пароли БД и Grafana, URL сервисов,
  параметры чанкинга — всё в `.env`. В репозитории есть `.env.example`, секретов в коде нет.
- **Настраиваемые порты.** `APP_PORT`, `FRONT_PORT`, `PROMETHEUS_PORT`, `GRAFANA_PORT` — если
  порт занят, достаточно поменять значение в `.env`.
- **Безопасность образа backend.** Запуск под non-root пользователем (`appuser`, uid 10001),
  встроенный HEALTHCHECK.
- **Provisioning Grafana.** Datasource Prometheus и дашборд заводятся автоматически при старте
  (provisioning), не нужно настраивать вручную.

---

## Как продемонстрировать на защите

1. Показать запуск **одной командой**: `cp .env.example .env && docker compose up --build`.
2. Показать, что поднялись все сервисы: `docker compose ps` (все healthy).
3. Открыть http://localhost:8000/health — все зависимости `up` (доказательство, что `app`
   дождался БД/ES/Redis).
4. Показать **CI**: вкладка Actions в GitHub — jobs `backend-lint-test`, `frontend-build`,
   `docker-build`; зелёный прогон при push в main.
5. Показать **мониторинг**:
   - Prometheus http://localhost:9090 → Status → Targets: `kb-backend` в состоянии UP;
   - Grafana http://localhost:3000 (admin/admin) → дашборд «KB Search — API Metrics»
     (rps поиска, total, p95/p50 latency). Сделать пару поисков, обновить дашборд.
6. Показать **init.sh**: `./init.sh` — скачивает 10 PDF-лекций и загружает их через API.
7. Показать, что порты настраиваются: изменить `FRONT_PORT` в `.env`, перезапустить.

---

## Возможные вопросы комиссии и ответы

**1. Зачем healthcheck и `depends_on: condition: service_healthy`?**
Обычный `depends_on` ждёт только старта контейнера, а не готовности сервиса. PostgreSQL и
особенно Elasticsearch стартуют долго. Healthcheck проверяет реальную готовность (`pg_isready`,
`_cluster/health`, `redis-cli ping`), а `condition: service_healthy` гарантирует, что `app`
не начнёт работать, пока зависимости не готовы — иначе были бы ошибки подключения на старте.

**2. Как устроен CI?**
`.github/workflows/ci.yml` запускается на push и PR в `main`. Три job:
`backend-lint-test` (ruff + pytest), `frontend-build` (tsc --noEmit + vite build) и
`docker-build`, который зависит от первых двух и собирает оба образа с кэшем GitHub Actions
(собирает, но не пушит — для учебного проекта достаточно проверки сборки).

**3. Почему multi-stage Dockerfile для фронтенда?**
Чтобы в финальном образе не было Node.js и исходников — только собранная статика и nginx.
Это уменьшает размер образа и поверхность атаки. Сборка идёт в стадии node, рантайм — nginx:alpine.

**4. Как настроен мониторинг и какие метрики собираете?**
Backend экспонирует `/metrics` (Prometheus instrumentator + кастомные метрики поиска).
Prometheus скрейпит `app:8000` каждые 10 с. Grafana с автоматически заведённым datasource
показывает дашборд: rps запросов к `/search`, общее число запросов и латентность p95/p50.
Это покрывает требование DO-06 (количество запросов к /search и время ответа).

**5. Как обеспечивается безопасность секретов?**
Все пароли и ключи — в `.env`, который не коммитится (в репозитории только `.env.example`
с заглушками). В `docker-compose.yml` сервисы читают `env_file: .env`. В коде секретов нет,
конфиг парсится из окружения через pydantic-settings.

**6. Что делает init.sh и почему бинарники не в репозитории?**
`init.sh` скачивает 10 PDF-лекций (статьи arXiv) во временную папку и загружает их через
`POST /api/v1/documents/upload`, после чего временную папку удаляет. По требованиям задания
в репозитории нельзя хранить бинарники (кроме `tests/fixtures`), поэтому документы скачиваются
на лету, а не лежат в git.

**7. Почему backend-контейнер работает под non-root?**
Это базовая практика безопасности контейнеров: если процесс скомпрометирован, у него нет
root-прав внутри контейнера. Создаётся пользователь `appuser` (uid 10001), ему принадлежат
приложение и том с загрузками.

**8. Как масштабировать систему в продакшене?**
Backend stateless (файлы на общем томе/объектном хранилище, состояние в БД), его можно
горизонтально масштабировать за балансировщиком. Elasticsearch и PostgreSQL выносятся в
кластер/управляемый сервис. Для учебного прототипа достаточно одного узла Compose.

**9. Что произойдёт при перезапуске? Данные сохранятся?**
Да: PostgreSQL, Elasticsearch, Redis и загруженные файлы хранятся в именованных Docker-томах
(`postgres_data`, `es_data`, `redis_data`, `uploads_data` и др.), которые переживают перезапуск
контейнеров. `restart: unless-stopped` поднимает сервисы после сбоя.

**10. Почему nginx проксирует /api, а не браузер ходит прямо на backend?**
Чтобы у фронтенда и API был один origin — это убирает проблемы CORS и упрощает деплой
(наружу открыт только один порт фронтенда). Backend не нужно публиковать наружу в продакшене.
