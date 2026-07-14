import { formatRelative } from "../format";
import type { AnalysisRead, ReaderArticle } from "../types";
import { SearchBar } from "./SearchBar";
import { SentimentBadge } from "./SentimentBadge";

interface Props {
  items: AnalysisRead[];
  page: number;
  hasMore: boolean;
  loading: boolean;
  query: string;
  onSearch: (query: string) => void;
  onPrev: () => void;
  onNext: () => void;
  onDelete: (id: string) => void;
  onOpen: (article: ReaderArticle) => void;
}

export function SavedList({
  items,
  page,
  hasMore,
  loading,
  query,
  onSearch,
  onPrev,
  onNext,
  onDelete,
  onOpen,
}: Props) {
  const emptyIcon = query ? "🔍" : "🗂️";
  const emptyText = query
    ? `No summaries match “${query}”.`
    : "No summaries yet. Summarise an article from your briefing.";

  return (
    <div className="saved">
      <div className="saved__search">
        <SearchBar
          onSearch={onSearch}
          loading={loading}
          placeholder="Search your summaries…"
          defaultValue={query}
          live
        />
      </div>

      {loading && items.length === 0 ? (
        <div className="empty">
          <div className="spinner" aria-label="Loading" />
        </div>
      ) : items.length === 0 && page === 0 ? (
        <div className="empty">
          <span className="empty__icon" aria-hidden>
            {emptyIcon}
          </span>
          <p>{emptyText}</p>
        </div>
      ) : (
        <>
          {items.length > 0 ? (
            <ul className="savedlist">
              {items.map((result) => (
                <li className="row" key={result.id}>
                  <div className="row__body">
                    <div className="row__head">
                      <button className="row__title" onClick={() => onOpen(result.article)}>
                        {result.article.title}
                      </button>
                      <span className="row__time">{formatRelative(result.created_at)}</span>
                    </div>
                    <div className="row__sub">
                      <SentimentBadge sentiment={result.sentiment} score={result.sentiment_score} />
                      <span className="row__src">
                        {result.article.source_name ?? "Unknown source"}
                      </span>
                    </div>
                    <p className="row__summary">{result.summary}</p>
                  </div>
                  <button
                    className="btn btn--ghost btn--small row__delete"
                    onClick={() => onDelete(result.id)}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty">
              <p>Nothing on this page.</p>
            </div>
          )}

          <div className="pager">
            <button
              className="btn btn--ghost btn--small"
              onClick={onPrev}
              disabled={page === 0 || loading}
            >
              ← Newer
            </button>
            <span className="pager__label">Page {page + 1}</span>
            <button
              className="btn btn--ghost btn--small"
              onClick={onNext}
              disabled={!hasMore || loading}
            >
              Older →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
