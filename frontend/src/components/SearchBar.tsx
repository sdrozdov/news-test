import { type FormEvent, useEffect, useRef, useState } from "react";

interface Props {
  onSearch: (query: string) => void;
  loading: boolean;
  placeholder?: string;
  defaultValue?: string;
  // When true, filter as the user types (debounced) with no submit button.
  live?: boolean;
}

export function SearchBar({ onSearch, loading, placeholder, defaultValue, live }: Props) {
  const [value, setValue] = useState(defaultValue ?? "");
  const firstRun = useRef(true);

  useEffect(() => {
    if (!live) return;
    // Skip the initial mount so we don't re-fire the search that's already loaded.
    if (firstRun.current) {
      firstRun.current = false;
      return;
    }
    const id = setTimeout(() => onSearch(value.trim()), 200);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, live]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSearch(value.trim());
  };

  return (
    <form className="search" onSubmit={submit}>
      <input
        className="search__input"
        type="search"
        placeholder={placeholder ?? "Search news… e.g. artificial intelligence"}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        aria-label={placeholder ?? "Search"}
      />
      {!live && (
        <button className="btn" type="submit" disabled={loading}>
          {loading ? "…" : "Search"}
        </button>
      )}
    </form>
  );
}
