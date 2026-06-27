import { type FormEvent } from "react";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  loading?: boolean;
}

export function SearchBar({ value, onChange, onSubmit, loading }: SearchBarProps) {
  const submit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  return (
    <form className="searchbar" role="search" onSubmit={submit}>
      <label htmlFor="search-input" className="visually-hidden">
        Поисковый запрос
      </label>
      <input
        id="search-input"
        data-testid="search-input"
        type="search"
        placeholder="Введите запрос, например: нейронные сети"
        value={value}
        autoComplete="off"
        onChange={(e) => onChange(e.target.value)}
      />
      <button
        type="submit"
        className="btn btn-primary"
        data-testid="search-button"
        disabled={loading || value.trim().length === 0}
      >
        {loading ? "Поиск…" : "Найти"}
      </button>
    </form>
  );
}
