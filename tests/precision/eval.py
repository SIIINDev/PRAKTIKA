"""QA-05 — Precision@3 evaluation for the knowledge-base search.

Pipeline:
  1. Generate 10 short DOCX files, each clearly about ONE distinct topic.
  2. Upload each via POST /api/v1/documents/upload and poll until status=done.
  3. For 10 reference queries (one per topic), call GET /api/v1/search.
  4. Compute Precision@3 = (relevant docs in top-3) / 3 for each query, plus the mean.
  5. Print a table and write tests/precision/REPORT.md.

A result is "relevant" for a query iff its file_name == the expected file for
that query (one-target-per-query relevance model). Precision@3 therefore caps
at 1/3 per query (a single relevant document), so the meaningful signal is
hit@3 (was the right doc anywhere in the top-3) and the resulting mean P@3.

Run:
    python3.12 -m venv tests/precision/.venv
    source tests/precision/.venv/bin/activate
    pip install -r tests/precision/requirements.txt
    python tests/precision/eval.py
"""

from __future__ import annotations

import os
import sys
import time
import tempfile
from dataclasses import dataclass

import requests
from docx import Document as Docx

BASE = os.environ.get("API_BASE", "http://localhost:8000/api/v1")
POLL_TIMEOUT_S = 60
POLL_INTERVAL_S = 1.0


@dataclass
class Topic:
    slug: str
    title: str          # human topic label, used in the doc heading
    body: str           # repeated topical sentences (gives the chunk substance)
    query: str          # reference query expected to retrieve this doc


# 10 distinct topics. Each body is written so its own vocabulary dominates,
# and the query uses words that should uniquely point back to that document.
TOPICS: list[Topic] = [
    Topic("neural", "Нейронные сети",
          "Нейронные сети состоят из слоёв искусственных нейронов. "
          "Обучение нейронной сети идёт методом обратного распространения ошибки. "
          "Глубокие нейронные сети применяются для распознавания образов.",
          "нейронные сети обучение нейронов"),
    Topic("rdbms", "Реляционные базы данных",
          "Реляционные базы данных хранят данные в таблицах со строками и столбцами. "
          "Язык SQL используется для запросов к реляционной базе данных. "
          "Нормализация устраняет избыточность в реляционной модели данных.",
          "реляционные базы данных таблицы SQL"),
    Topic("mergesort", "Сортировка слиянием",
          "Сортировка слиянием делит массив пополам и сливает отсортированные части. "
          "Сложность сортировки слиянием составляет O(n log n). "
          "Слияние двух отсортированных подмассивов выполняется за линейное время.",
          "сортировка слиянием массива O(n log n)"),
    Topic("tcp", "Протокол TCP",
          "Протокол TCP обеспечивает надёжную доставку пакетов по сети. "
          "TCP устанавливает соединение трёхэтапным рукопожатием. "
          "Управление потоком и повторная передача гарантируют доставку сегментов TCP.",
          "протокол TCP надёжная доставка пакетов соединение"),
    Topic("os", "Операционные системы",
          "Операционная система управляет процессами и распределяет память. "
          "Планировщик операционной системы переключает процессы на процессоре. "
          "Виртуальная память и системные вызовы — основа операционной системы.",
          "операционная система процессы планировщик память"),
    Topic("compilers", "Компиляторы",
          "Компилятор переводит исходный код в машинный через лексический и синтаксический анализ. "
          "Компилятор строит абстрактное синтаксическое дерево и генерирует код. "
          "Оптимизация компилятора повышает эффективность результирующей программы.",
          "компилятор лексический синтаксический анализ генерация кода"),
    Topic("rsa", "Криптография RSA",
          "Криптография RSA основана на сложности факторизации больших чисел. "
          "Алгоритм RSA использует открытый и закрытый ключи для шифрования. "
          "Безопасность RSA опирается на модульную арифметику и простые числа.",
          "криптография RSA открытый закрытый ключ шифрование"),
    Topic("ml", "Машинное обучение",
          "Машинное обучение строит модели на основе обучающих данных. "
          "Обучение с учителем и без учителя — основные парадигмы машинного обучения. "
          "Переобучение модели снижает качество обобщения в машинном обучении.",
          "машинное обучение модели обучающие данные с учителем"),
    Topic("graphs", "Теория графов",
          "Теория графов изучает вершины и рёбра графа. "
          "Обход графа в ширину и в глубину находит пути между вершинами. "
          "Деревья и связные компоненты — базовые понятия теории графов.",
          "теория графов вершины рёбра обход графа"),
    Topic("automata", "Конечные автоматы",
          "Конечный автомат имеет множество состояний и переходы между ними. "
          "Детерминированный конечный автомат распознаёт регулярные языки. "
          "Конечные автоматы применяются в лексическом анализе и распознавании строк.",
          "конечный автомат состояния переходы регулярные языки"),
]


def make_docx(topic: Topic, path: str) -> None:
    doc = Docx()
    doc.add_heading(topic.title, level=1)
    # Repeat the body a few times so the document has substantive, on-topic text.
    for _ in range(6):
        doc.add_paragraph(topic.body)
    doc.save(path)


def upload(path: str, file_name: str) -> str:
    with open(path, "rb") as fh:
        files = {"file": (file_name,
                          fh,
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        r = requests.post(f"{BASE}/documents/upload", files=files, timeout=30)
    if r.status_code != 202:
        raise RuntimeError(f"upload {file_name} failed: HTTP {r.status_code} {r.text}")
    return r.json()["id"]


def wait_done(doc_id: str, file_name: str) -> None:
    deadline = time.time() + POLL_TIMEOUT_S
    while time.time() < deadline:
        r = requests.get(f"{BASE}/documents/{doc_id}", timeout=30)
        r.raise_for_status()
        status = r.json()["status"]
        if status == "done":
            return
        if status == "error":
            raise RuntimeError(f"{file_name} indexing error: {r.json().get('error_message')}")
        time.sleep(POLL_INTERVAL_S)
    raise TimeoutError(f"{file_name} not indexed within {POLL_TIMEOUT_S}s")


def search_top3_files(query: str) -> list[str]:
    r = requests.get(f"{BASE}/search", params={"q": query, "page": 1, "size": 10}, timeout=30)
    r.raise_for_status()
    results = r.json()["results"]
    # Deduplicate file names preserving rank order, then take the top 3.
    seen: list[str] = []
    for item in results:
        fn = item["file_name"]
        if fn not in seen:
            seen.append(fn)
        if len(seen) == 3:
            break
    return seen


def main() -> int:
    print(f"API_BASE = {BASE}")
    tmpdir = tempfile.mkdtemp(prefix="qa05_docs_")
    expected_files: dict[str, str] = {}  # slug -> file_name

    print("\n[1/3] Generating + uploading 10 topic documents...")
    for t in TOPICS:
        file_name = f"qa05_{t.slug}.docx"
        path = os.path.join(tmpdir, file_name)
        make_docx(t, path)
        doc_id = upload(path, file_name)
        wait_done(doc_id, file_name)
        expected_files[t.slug] = file_name
        print(f"  indexed: {file_name}")

    print("\n[2/3] Running 10 reference queries...")
    rows = []
    hits = 0
    precision_sum = 0.0
    for t in TOPICS:
        expected = expected_files[t.slug]
        top3 = search_top3_files(t.query)
        hit = expected in top3
        # Single relevant target per query -> at most 1 relevant in top-3.
        relevant_in_top3 = 1 if hit else 0
        p_at_3 = relevant_in_top3 / 3.0
        precision_sum += p_at_3
        hits += 1 if hit else 0
        rows.append((t.query, expected, top3, hit, p_at_3))

    mean_p3 = precision_sum / len(TOPICS)
    hit_rate = hits / len(TOPICS)

    # Console table.
    print("\n[3/3] Results\n")
    header = f"{'query':<45} {'expected':<22} {'hit@3':<6} {'P@3':<6}"
    print(header)
    print("-" * len(header))
    for query, expected, top3, hit, p3 in rows:
        print(f"{query[:44]:<45} {expected:<22} {('YES' if hit else 'no'):<6} {p3:.3f}")
    print("-" * len(header))
    print(f"hit@3 rate: {hit_rate:.0%}   mean Precision@3: {mean_p3:.3f}")

    # Markdown report.
    lines = []
    lines.append("# QA-05 — Precision@3 Report\n")
    lines.append(f"API base: `{BASE}`\n")
    lines.append("Relevance model: exactly one target document per query "
                 "(file name must match). With a single relevant target, "
                 "Precision@3 caps at 1/3 per query; **hit@3** = right doc "
                 "anywhere in the top 3.\n")
    lines.append("| query | expected file | top-3 files | hit@3 | P@3 |")
    lines.append("|---|---|---|---|---|")
    for query, expected, top3, hit, p3 in rows:
        top3_str = "<br>".join(top3) if top3 else "(none)"
        lines.append(f"| {query} | `{expected}` | {top3_str} | "
                     f"{'YES' if hit else 'no'} | {p3:.3f} |")
    lines.append("")
    lines.append(f"**hit@3 rate: {hit_rate:.0%}**")
    lines.append("")
    lines.append(f"**Mean Precision@3: {mean_p3:.3f}**")
    lines.append("")

    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "REPORT.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"\nWrote {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
