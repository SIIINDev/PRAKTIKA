# CLAUDE.md — Knowledge Base Search (учебная практика БПИ24)

Intelligent full-text search system over a university knowledge base. Team of 4: **BE / FE / DO / QA**.
Assignment: `Задание на учебную практику БПИ24.pdf`. Requirement IDs (BE-01…, FE-01…, DO-01…, QA-01…) are traceable in `docs/REQUIREMENTS_TRACEABILITY.md`.

## Stack
Python 3.12 + FastAPI · React 18 + TypeScript + Vite · PostgreSQL 16 · Elasticsearch 8 (russian analyzer) · Redis · Docker Compose · GitHub Actions · pytest + Playwright + Locust.

## Run
```bash
cp .env.example .env
docker compose up --build        # http://localhost:8080 (UI), http://localhost:8000/docs (API)
./init.sh                        # download 10 sample lectures and index them
```

## Rules
- The API shape is fixed in `docs/API_CONTRACT.md` — change both BE and FE together.
- Commits use Conventional Commits: `feat: …`, `fix: …`, `test: …`, `docs: …`, `chore: …`.
- No binaries in the repo except `tests/fixtures/`.
- Public functions/classes have docstrings (params, returns). PEP 8 / ruff clean.
- Secrets only via `.env` (`.env.example` committed, `.env` ignored).
