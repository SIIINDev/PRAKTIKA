import { useState } from "react";
import { HomePage } from "./pages/HomePage";
import { SearchPage } from "./pages/SearchPage";

type Tab = "documents" | "search";

export default function App() {
  const [tab, setTab] = useState<Tab>("documents");

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true">
              📚
            </span>
            <span>База знаний</span>
          </div>
          <nav className="nav" aria-label="Основная навигация">
            <button
              type="button"
              className={`nav-link${tab === "documents" ? " active" : ""}`}
              aria-current={tab === "documents" ? "page" : undefined}
              data-testid="nav-documents"
              onClick={() => setTab("documents")}
            >
              Документы
            </button>
            <button
              type="button"
              className={`nav-link${tab === "search" ? " active" : ""}`}
              aria-current={tab === "search" ? "page" : undefined}
              data-testid="nav-search"
              onClick={() => setTab("search")}
            >
              Поиск
            </button>
          </nav>
        </div>
      </header>

      <main className="page">
        {tab === "documents" ? <HomePage /> : <SearchPage />}
      </main>
    </div>
  );
}
