# QA-02 — Playwright E2E (critical search flow)

End-to-end test of the knowledge-base critical path against the **already-running**
stack (frontend `http://localhost:8080`, backend `http://localhost:8000`).

## What it covers (`specs/search-flow.spec.ts`)

1. Open the app and navigate to **Документы** (`nav-documents`).
2. Upload `tests/fixtures/lecture_databases.docx` via the hidden `file-input`
   (`setInputFiles`).
3. Poll the matching `doc-list-item` until its status badge reads **Готово**
   (`[data-status="done"]`, up to 30 s).
4. Switch to **Поиск** (`nav-search`), fill `search-input` with `база данных`,
   click `search-button`.
5. Assert ≥ 1 `result-card` with a file name (`.result-file`), a numeric score
   (`.result-score`, `N.NN`) and at least one `<mark>` highlight.
6. Search gibberish `zzzнетакого` and assert `empty-state` shows the
   "…ничего не найдено…" message and there are zero result cards.

Note: the backend returns highlights wrapped in `<em>`; the frontend `Highlight`
component safely re-renders those as `<mark>`, which is what the test asserts.

## How to run

The stack must already be up (this config has **no** `webServer` block).

```bash
cd tests/e2e
npm install
npx playwright install chromium
npx playwright test --reporter=line
```

## Last result (real run)

```
Running 1 test using 1 worker

[1/1] [chromium] › specs/search-flow.spec.ts:8:7 › Knowledge-base critical path › upload a DOCX, index it, search and see highlighted results, then empty state
  1 passed (3.3s)
```

**1 passed** — full critical path (upload → index → search → highlight → empty state) green.
