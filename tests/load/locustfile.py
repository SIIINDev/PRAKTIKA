"""QA-04 — Locust load test for the knowledge-base search API.

Hammers GET /api/v1/search?q=... with a small pool of Russian queries.

Run headless, 50 users, ~60s:

    locust -f tests/load/locustfile.py --headless -u 50 -r 10 -t 60s \
        --host http://localhost:8000 --csv tests/load/result
"""

import random

from locust import HttpUser, between, task

QUERIES = [
    "база данных",
    "алгоритм",
    "поиск",
    "сортировка",
    "индекс",
]


class SearchUser(HttpUser):
    # Think-time between requests: 0.5 .. 2.0 seconds.
    wait_time = between(0.5, 2.0)

    @task
    def search(self):
        q = random.choice(QUERIES)
        # name= groups all queries under one stable label in the stats table.
        with self.client.get(
            "/api/v1/search",
            params={"q": q, "page": 1, "size": 10},
            name="/api/v1/search?q=[ru]",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"HTTP {resp.status_code}")
            else:
                resp.success()
