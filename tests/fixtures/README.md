# Test fixtures (QA-03)

Binary documents kept here on purpose — the assignment permits binaries only under
`tests/fixtures/`. Regenerate with `python scripts/make_fixtures.py`.

| File | Purpose |
|------|---------|
| `lecture_databases.docx` | Valid DOCX, Russian text — happy-path upload/index/search |
| `lecture_algorithms.pdf` | Valid 2-page PDF, Russian text — exercises page numbers |
| `empty.pdf` | Zero-byte file — extractor must fail cleanly → status `error` |
| `broken.pdf` | Corrupt PDF body — extractor must fail cleanly → status `error` |
| `notes.txt` | Wrong type — upload must be rejected with HTTP 400 |
