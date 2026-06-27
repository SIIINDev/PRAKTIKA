import type { SearchResultItem } from "../services/api";
import { Highlight } from "./Highlight";

export function ResultCard({ item }: { item: SearchResultItem }) {
  // Prefer the highlighted fragment; fall back to plain text (escaped by React).
  const hasHighlight = item.highlight && item.highlight.length > 0;

  return (
    <article className="result-card" data-testid="result-card">
      <div className="result-head">
        <div>
          <span className="result-file">{item.file_name}</span>
          <span className="result-sub"> · стр. {item.page}</span>
        </div>
        <span className="result-score" title="Релевантность">
          {item.score.toFixed(2)}
        </span>
      </div>
      <p className="result-text">
        {hasHighlight ? <Highlight html={item.highlight} /> : item.text}
      </p>
    </article>
  );
}
