# Инструкция по самостоятельной проверке (приёмочный чек-лист)

Документ позволяет вручную убедиться, что система отвечает **всем** критериям задания.
Каждый пункт привязан к ID требования, содержит точную команду / действие и ожидаемый результат.

> На этой машине порты Prometheus/Grafana были смещены (9090/3000 заняты другими процессами),
> поэтому реальные URL: **Prometheus `:9091`**, **Grafana `:3001`**. На чистой машине будут стандартные
> `:9090` / `:3000` (см. `.env.example`).

## URL-адреса работающего стенда

| Что | URL |
|-----|-----|
| Веб-интерфейс (SPA) | http://localhost:8080 |
| API + Swagger UI | http://localhost:8000/docs |
| OpenAPI JSON | http://localhost:8000/openapi.json |
| Health | http://localhost:8000/health |
| Метрики Prometheus-формата | http://localhost:8000/metrics |
| Prometheus | http://localhost:9091 |
| Grafana (admin / admin) | http://localhost:3001 |

---

## 0. Поднять стек

### Вариант А — проверить как есть (стек уже запущен)
```bash
cd ~/Documents/GitHub/PRAKTIKA
docker compose ps          # все сервисы Up; postgres/elasticsearch/redis/app — healthy
curl -s localhost:8000/health
# {"status":"ok","elasticsearch":"up","redis":"up","postgres":"up"}
```

### Вариант Б — чистый запуск «с нуля» (как у комиссии)
```bash
cd ~/Documents/GitHub/PRAKTIKA
cp .env.example .env                 # секреты только из .env
docker compose down -v               # стереть тома (чистая БД и индекс)
docker compose up --build -d         # одна команда поднимает всё
# дождаться, пока app станет healthy:
until curl -sf localhost:8000/health >/dev/null; do sleep 2; done
./init.sh                            # DO-07: скачать 10 PDF-лекций и загрузить
```
> На чистой машине, где свободны порты 9090/3000, открой Grafana на `:3000`, Prometheus на `:9090`.
> Если порт занят — поменяй `APP_PORT/FRONT_PORT/PROMETHEUS_PORT/GRAFANA_PORT` в `.env`.

---

## 1. Backend (BE-01…BE-10) — через curl

Открой второй терминал. Команды самодостаточны.

### BE-01 — загрузка документа
```bash
curl -s -X POST localhost:8000/api/v1/documents/upload \
  -F "file=@tests/fixtures/lecture_databases.docx"
# Ожидание: HTTP 202, JSON {"id":"<uuid>","file_name":"lecture_databases.docx","status":"uploading"}
```

### BE-02 — валидация формата и размера (HTTP 400)
```bash
# неверный тип
curl -s -o /dev/null -w "txt -> %{http_code}\n" \
  -X POST localhost:8000/api/v1/documents/upload -F "file=@tests/fixtures/notes.txt"
# Ожидание: 400

# слишком большой файл (>20 МБ)
head -c 22000000 /dev/zero | tr '\0' 'a' > /tmp/big.docx
curl -s -o /dev/null -w "big -> %{http_code}\n" \
  -X POST localhost:8000/api/v1/documents/upload -F "file=@/tmp/big.docx"
# Ожидание: 400
```

### BE-03 / BE-04 / BE-05 / BE-07 — UUID, извлечение текста, чанкинг, метаданные
```bash
# загрузить PDF и проследить статус до "done"
ID=$(curl -s -X POST localhost:8000/api/v1/documents/upload \
  -F "file=@tests/fixtures/lecture_algorithms.pdf" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
echo "UUID: $ID"                                  # BE-03: валидный UUID
for i in $(seq 1 10); do sleep 1; \
  curl -s localhost:8000/api/v1/documents/$ID | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["status"],"chunks=",d["chunk_count"])'; done
# Ожидание: статус дойдёт до "done", chunk_count > 0 (BE-04 извлекло текст, BE-05 разбило на чанки)
```

### BE-06 — Elasticsearch + русский анализатор (морфология)
```bash
# документ содержит "базы данных", а ищем форму "база данных" — стемминг должен найти
curl -s -G localhost:8000/api/v1/search --data-urlencode "q=база данных" \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print("total:",d["total"])'
# Ожидание: total > 0 (русский анализатор привёл словоформы к одной основе)
```

### BE-08 / BE-09 — поиск multi_match, ранжирование, поля JSON
```bash
curl -s -G localhost:8000/api/v1/search --data-urlencode "q=алгоритм" \
  | python3 -c '
import sys,json
d=json.load(sys.stdin)
r=d["results"][0]
print("ключи результата:", list(r.keys()))         # BE-09: chunk_id,file_name,page,text,score,...
print("scores:", [round(x["score"],2) for x in d["results"]])  # BE-08: по убыванию'
# Ожидание: есть chunk_id,file_name,page,text,score; scores не возрастают
```

### BE-10 — кеш Redis (TTL 5 мин)
```bash
curl -s -G localhost:8000/api/v1/search --data-urlencode "q=нейронные сети" | python3 -c 'import sys,json;print("cached:",json.load(sys.stdin)["cached"])'
curl -s -G localhost:8000/api/v1/search --data-urlencode "q=нейронные сети" | python3 -c 'import sys,json;print("cached:",json.load(sys.stdin)["cached"])'
# Ожидание: первый раз cached: False, второй раз cached: True
```

### Коды ответов API
```bash
curl -s -o /dev/null -w "empty q  -> %{http_code} (400)\n" "localhost:8000/api/v1/search?q="
curl -s -o /dev/null -w "no doc   -> %{http_code} (404)\n" localhost:8000/api/v1/documents/00000000-0000-0000-0000-000000000000
curl -s -o /dev/null -w "openapi  -> %{http_code} (200)\n" localhost:8000/openapi.json
```
Открой **http://localhost:8000/docs** — Swagger UI со всеми эндпоинтами (OpenAPI 3.0).

---

## 2. Frontend (FE-01…FE-09) — в браузере

Открой **http://localhost:8080**.

| ID | Что сделать | Ожидаемый результат |
|----|-------------|---------------------|
| FE-01 | Вкладка «Документы». Перетащи PDF/DOCX в область загрузки **или** кликни и выбери несколько файлов | Зона drag-and-drop принимает несколько файлов |
| FE-02 | Наблюдай за только что загруженным файлом | Прогресс-бар и смена статусов: **Загрузка… → Индексация… → Готово** (битый файл → **Ошибка**) |
| FE-03 | Список «Загруженные документы» | Имя, дата, размер, число фрагментов, статус; есть кнопка «Удалить» |
| FE-04 | Вкладка «Поиск». Введи `модель` и нажми **Найти**; затем введи запрос и нажми **Enter** | Поиск срабатывает и по кнопке, и по Enter |
| FE-05 | Посмотри карточки результатов | В каждой: имя файла, № страницы, фрагмент текста, оценка релевантности |
| FE-06 | Найди слова из запроса в карточках | Совпадения подсвечены **жёлтым фоном** |
| FE-07 | Поиск `model` (много результатов) | Пагинация внизу; переключение страниц меняет выдачу (по 10 на страницу) |
| FE-08 | Поиск `zzzнетакого123` | Сообщение: **«По вашему запросу ничего не найдено. Попробуйте изменить формулировку»** |
| FE-09 | Сузь окно браузера до ~320px и расширь до ~1920px (или DevTools → device toolbar) | Нет горизонтальной прокрутки, вёрстка перестраивается |

Доступность (по желанию): DevTools → Lighthouse / axe — на обеих вкладках 0 нарушений.

---

## 3. DevOps (DO-01…DO-07)

```bash
# DO-03: одна команда поднимает все сервисы; конфиг валиден
docker compose config -q && echo "compose OK"
docker compose ps          # app/front/postgres/elasticsearch/redis (+prometheus/grafana)

# DO-01/02: образы собраны (Python+FastAPI backend, Node→Nginx frontend)
docker compose build app front

# DO-04: секреты только в .env; .env.example в репозитории
grep -i password docker-compose.yml      # только ${...}, без хардкода
ls -1 .env.example

# DO-07: сидинг 10 PDF через API
./init.sh                                 # uploaded=10
```

- **DO-05 (CI):** файл `.github/workflows/ci.yml`. На GitHub открой вкладку **Actions** —
  при push в `main` запускаются `backend-lint-test` (ruff+pytest), `frontend-build` (tsc+build),
  `docker-build`. Локально повторить:
  ```bash
  cd backend && python3.12 -m venv .venv && source .venv/bin/activate \
    && pip install -r requirements.txt -r requirements-dev.txt && ruff check . && pytest
  cd ../frontend && npm ci && npx tsc --noEmit && npm run build
  ```
- **DO-06 (мониторинг):**
  ```bash
  # сгенерировать трафик, затем посмотреть метрику
  for i in $(seq 1 5); do curl -s -G localhost:8000/api/v1/search --data-urlencode "q=data" >/dev/null; done
  curl -s 'localhost:9091/api/v1/query?query=kb_search_requests_total' | python3 -m json.tool | head -20
  ```
  Открой **http://localhost:9091/targets** — цель `kb-backend` в состоянии **UP**.
  Открой **http://localhost:3001** (admin/admin) → Dashboards → **«KB Search — API Metrics»**:
  панели по числу запросов к `/search` и времени ответа.

---

## 4. Тестирование (QA-01…QA-06)

### QA-01 — юнит-тесты + покрытие ≥50%
```bash
cd backend && source .venv/bin/activate    # (или создать venv как выше)
pytest
# Ожидание: 27 passed, покрытие TOTAL ~64% (>50%)
```

### QA-02 — E2E (Playwright)
```bash
cd tests/e2e && npm install && npx playwright install chromium
npx playwright test --reporter=line
# Ожидание: 1 passed (загрузка → индексация → поиск → подсветка → пустое состояние)
```

### QA-03 — тестовые документы
```bash
ls tests/fixtures   # lecture_databases.docx, lecture_algorithms.pdf, empty.pdf, broken.pdf, notes.txt
# битый PDF → статус error; пустой/неверный тип → 400 (см. раздел BE-02)
```

### QA-04 — нагрузочный тест (50 пользователей)
```bash
cd tests/load && python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
locust -f locustfile.py --headless -u 50 -r 10 -t 60s --host http://localhost:8000 --csv result
# Готовый отчёт: tests/load/REPORT.md (50 польз./60с: 2274 запроса, 0 ошибок, p50 4 мс, p95 8 мс)
```

### QA-05 — качество поиска Precision@3
```bash
cd tests/precision && python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python eval.py
# Таблица в tests/precision/REPORT.md: hit@3 = 100%, средний Precision@3 = 0.333
```

### QA-06 — руководство пользователя
Открой `docs/USER_GUIDE.md`.

---

## 5. Итоговый приёмочный чек-лист

- [ ] `docker compose up` поднимает весь стек одной командой, `/health` → всё `up`.
- [ ] BE-01..10: загрузка, валидация (400), UUID, парсинг PDF+DOCX, чанкинг, ES-поиск, JSON-поля, Redis-кеш.
- [ ] FE-01..09: drag-drop, прогресс-статусы, список, поиск (кнопка+Enter), карточки, жёлтая подсветка, пагинация, пустое состояние, адаптив.
- [ ] DO-01..07: Dockerfile×2, compose из 5+ сервисов, секреты в .env, CI, мониторинг, init.sh.
- [ ] QA-01..06: юнит-тесты ≥50% (факт 64%), E2E, тестовые файлы, нагрузка (0 ошибок), Precision@3 (hit@3 100%), User Guide.
- [ ] Swagger `/docs`, README, документация по ролям `docs/roles/*`, матрица трассировки `docs/REQUIREMENTS_TRACEABILITY.md`.

Полная карта «требование → файл → как проверено» — в **`docs/REQUIREMENTS_TRACEABILITY.md`**.
