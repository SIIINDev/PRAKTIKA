import { useCallback, useEffect, useRef, useState } from "react";
import { SearchBar } from "../components/SearchBar";
import { ResultCard } from "../components/ResultCard";
import { Pagination } from "../components/Pagination";
import { EmptyState } from "../components/EmptyState";
import {
  type SearchHistoryItem,
  type SearchResponse,
  getSearchHistory,
  search,
} from "../services/api";

const PAGE_SIZE = 10;
const NO_RESULTS_MESSAGE =
  "По вашему запросу ничего не найдено. Попробуйте изменить формулировку";

export function SearchPage() {
  const [input, setInput] = useState("");
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<SearchHistoryItem[]>([]);
  // The query string that produced the current results (for stable pagination).
  const activeQuery = useRef<string>("");
  const abortRef = useRef<AbortController | null>(null);

  const loadHistory = useCallback(async () => {
    try {
      const data = await getSearchHistory();
      setHistory(data.history);
    } catch {
      /* history is non-critical */
    }
  }, []);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const runSearch = useCallback(
    async (query: string, page: number) => {
      const trimmed = query.trim();
      if (trimmed.length === 0) return;

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      activeQuery.current = trimmed;
      setLoading(true);
      setError(null);
      try {
        const data = await search(trimmed, page, PAGE_SIZE, controller.signal);
        setResponse(data);
        void loadHistory();
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Ошибка поиска");
        setResponse(null);
      } finally {
        if (abortRef.current === controller) setLoading(false);
      }
    },
    [loadHistory],
  );

  const onSubmit = useCallback(() => {
    void runSearch(input, 1);
  }, [input, runSearch]);

  const onPageChange = useCallback(
    (page: number) => {
      void runSearch(activeQuery.current, page);
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    [runSearch],
  );

  const onHistoryClick = useCallback(
    (query: string) => {
      setInput(query);
      void runSearch(query, 1);
    },
    [runSearch],
  );

  const totalPages = response ? Math.max(1, Math.ceil(response.total / response.size)) : 0;
  const hasSearched = response !== null;

  return (
    <div>
      <div className="card card-pad">
        <h2 className="section-title">Поиск по базе знаний</h2>
        <SearchBar
          value={input}
          onChange={setInput}
          onSubmit={onSubmit}
          loading={loading}
        />

        {history.length > 0 && (
          <div className="history" aria-label="История запросов">
            {history.slice(0, 8).map((h, i) => (
              <button
                type="button"
                key={`${h.query}-${i}`}
                className="chip"
                onClick={() => onHistoryClick(h.query)}
                title={`${h.results_count} результат(ов)`}
              >
                {h.query}
              </button>
            ))}
          </div>
        )}
      </div>

      {error ? (
        <div className="error-banner" role="alert" style={{ marginTop: 16 }}>
          {error}
        </div>
      ) : null}

      {loading && !response ? (
        <div className="state">
          <span className="spinner" aria-hidden="true" />
          <div style={{ marginTop: 10 }}>Ищем…</div>
        </div>
      ) : hasSearched ? (
        <div style={{ marginTop: 8 }}>
          <div className="search-meta">
            <span>
              Найдено: <strong>{response!.total}</strong> по запросу «{response!.query}»
            </span>
            <span>·</span>
            <span>{response!.took_ms} мс</span>
            {response!.cached ? <span className="cached-tag">из кэша</span> : null}
          </div>

          {response!.results.length === 0 ? (
            <EmptyState
              icon="🤔"
              message={NO_RESULTS_MESSAGE}
              testId="empty-state"
            />
          ) : (
            <>
              <div className="results">
                {response!.results.map((item) => (
                  <ResultCard key={item.chunk_id} item={item} />
                ))}
              </div>
              <Pagination
                page={response!.page}
                totalPages={totalPages}
                onChange={onPageChange}
              />
            </>
          )}
        </div>
      ) : (
        <EmptyState
          icon="💡"
          title="Начните поиск"
          message="Введите запрос и нажмите «Найти» или клавишу Enter."
        />
      )}
    </div>
  );
}
