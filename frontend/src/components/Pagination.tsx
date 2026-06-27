interface PaginationProps {
  page: number;
  totalPages: number;
  onChange: (page: number) => void;
}

/** Builds a compact list of page tokens: numbers and "…" ellipses. */
function buildPages(page: number, total: number): (number | "…")[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  const pages: (number | "…")[] = [1];
  const start = Math.max(2, page - 1);
  const end = Math.min(total - 1, page + 1);
  if (start > 2) pages.push("…");
  for (let p = start; p <= end; p++) pages.push(p);
  if (end < total - 1) pages.push("…");
  pages.push(total);
  return pages;
}

export function Pagination({ page, totalPages, onChange }: PaginationProps) {
  if (totalPages <= 1) return null;
  const tokens = buildPages(page, totalPages);

  return (
    <nav className="pagination" data-testid="pagination" aria-label="Постраничная навигация">
      <button
        type="button"
        className="page-btn"
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
        aria-label="Предыдущая страница"
      >
        ‹
      </button>

      {tokens.map((tok, idx) =>
        tok === "…" ? (
          <span className="page-ellipsis" key={`e-${idx}`} aria-hidden="true">
            …
          </span>
        ) : (
          <button
            type="button"
            key={tok}
            className={`page-btn${tok === page ? " active" : ""}`}
            aria-current={tok === page ? "page" : undefined}
            aria-label={`Страница ${tok}`}
            onClick={() => onChange(tok)}
          >
            {tok}
          </button>
        ),
      )}

      <button
        type="button"
        className="page-btn"
        onClick={() => onChange(page + 1)}
        disabled={page >= totalPages}
        aria-label="Следующая страница"
      >
        ›
      </button>
    </nav>
  );
}
