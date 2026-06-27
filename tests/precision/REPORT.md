# QA-05 — Precision@3 Report

API base: `http://localhost:8000/api/v1`

Relevance model: exactly one target document per query (file name must match). With a single relevant target, Precision@3 caps at 1/3 per query; **hit@3** = right doc anywhere in the top 3.

| query | expected file | top-3 files | hit@3 | P@3 |
|---|---|---|---|---|
| нейронные сети обучение нейронов | `qa05_neural.docx` | qa05_neural.docx<br>qa05_ml.docx<br>qa05_tcp.docx | YES | 0.333 |
| реляционные базы данных таблицы SQL | `qa05_rdbms.docx` | qa05_rdbms.docx<br>lecture_databases.docx | YES | 0.333 |
| сортировка слиянием массива O(n log n) | `qa05_mergesort.docx` | qa05_mergesort.docx<br>lecture_algorithms.pdf<br>attention-is-all-you-need.pdf | YES | 0.333 |
| протокол TCP надёжная доставка пакетов соединение | `qa05_tcp.docx` | qa05_tcp.docx | YES | 0.333 |
| операционная система процессы планировщик память | `qa05_os.docx` | qa05_os.docx | YES | 0.333 |
| компилятор лексический синтаксический анализ генерация кода | `qa05_compilers.docx` | qa05_compilers.docx<br>qa05_automata.docx | YES | 0.333 |
| криптография RSA открытый закрытый ключ шифрование | `qa05_rsa.docx` | qa05_rsa.docx | YES | 0.333 |
| машинное обучение модели обучающие данные с учителем | `qa05_ml.docx` | qa05_ml.docx<br>lecture_databases.docx<br>qa05_rdbms.docx | YES | 0.333 |
| теория графов вершины рёбра обход графа | `qa05_graphs.docx` | qa05_graphs.docx<br>lecture_algorithms.pdf<br>lecture_databases.docx | YES | 0.333 |
| конечный автомат состояния переходы регулярные языки | `qa05_automata.docx` | qa05_automata.docx<br>lecture_databases.docx<br>qa05_rdbms.docx | YES | 0.333 |

**hit@3 rate: 100%**

**Mean Precision@3: 0.333**
