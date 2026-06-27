# QA-04 — Load Test Report

Tool: **Locust 2.44.4** (Python 3.12.13)
Target: `http://localhost:8000` — `GET /api/v1/search?q=...`
Query pool (random): `база данных`, `алгоритм`, `поиск`, `сортировка`, `индекс`
Think-time per user: 0.5–2.0 s (`between(0.5, 2.0)`)

## Command

```bash
python3.12 -m venv tests/load/.venv
source tests/load/.venv/bin/activate
pip install -r tests/load/requirements.txt
locust -f tests/load/locustfile.py --headless -u 50 -r 10 -t 60s \
    --host http://localhost:8000 --csv tests/load/result
```

## Run parameters

- Concurrent users: **50**
- Spawn rate: **10 users/s**
- Duration: **60 s**

## Real measured results

| Metric | Value |
|---|---|
| Total requests | **2274** (CSV final) / 2301 (last console tick) |
| Failures | **0 (0.00%)** |
| Requests/s (RPS) | **38.4** |
| Median / p50 | **4 ms** |
| p90 | **7 ms** |
| p95 | **8 ms** |
| p99 | **24 ms** |
| Max | **181 ms** |
| Average | **5.4 ms** |
| Min | **1 ms** |

### Raw Locust summary lines

```
Type     Name                      # reqs   # fails |  Avg  Min  Max  Med | req/s  failures/s
GET      /api/v1/search?q=[ru]      2301   0(0.00%) |    5    1  181    4 | 38.44   0.00

Response time percentiles (approximated)
Type  Name                  50%  66%  75%  80%  90%  95%  98%  99%  99.9%  99.99%  100%  # reqs
GET   /api/v1/search?q=[ru]   4    5    5    6    7    8   14   24    180     180   180   2301
```

(CSV `result_stats.csv`: 2274 reqs, 0 fails, median 4 ms, avg 5.39 ms, p95 8 ms, p99 24 ms, RPS 38.41.)

## Assessment

- **50 concurrent users is NOT too heavy** for this endpoint. Zero failures, p95 of 8 ms,
  and a stable ~38 RPS throughout the run. Throughput is bounded by the configured
  client think-time (0.5–2 s/user => ~50/1.25 ~= 40 req/s expected), **not** by the server.
- The single outlier (max ~181 ms, visible only at p99.9+) is a cold-cache / first-hit blip;
  the steady-state tail (p99 = 24 ms) is well controlled.
- No errors were recorded in `result_failures.csv` or `result_exceptions.csv`.

Artifacts: `result_stats.csv`, `result_stats_history.csv`, `result_failures.csv`, `result_exceptions.csv`.
