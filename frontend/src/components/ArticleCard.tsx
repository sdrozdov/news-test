import { useState } from "react";

import { formatRelative, safeHref } from "../format";
import type { NewsArticle, Sentiment } from "../types";
import { SentimentBadge } from "./SentimentBadge";

interface Props {
  article: NewsArticle;
  analyzedSentiment?: Sentiment;
  busy: boolean;
  error?: string;
  onAnalyze: () => void;
  onOpen: () => void;
}

export function ArticleCard({
  article,
  analyzedSentiment,
  busy,
  error,
  onAnalyze,
  onOpen,
}: Props) {
  const [imgFailed, setImgFailed] = useState(false);
  const imageSrc = safeHref(article.image_url);

  return (
    <article className="card">
      <button className="card__imgbtn" onClick={onOpen} aria-label={`Read: ${article.title}`}>
        {imageSrc && !imgFailed ? (
          <img
            className="card__img"
            src={imageSrc}
            alt=""
            loading="lazy"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <span className="card__img card__img--placeholder" aria-hidden>
            ◆
          </span>
        )}
      </button>
      <div className="card__body">
        <div className="card__meta">
          <span className="card__source">{article.source_name ?? "Unknown source"}</span>
          {article.published_at && <span>· {formatRelative(article.published_at)}</span>}
        </div>
        <button className="card__title" onClick={onOpen}>
          {article.title}
        </button>
        {article.description && <p className="card__desc">{article.description}</p>}
        <div className="card__actions">
          <button className="btn btn--small" onClick={onAnalyze} disabled={busy}>
            {busy ? "Summarising…" : analyzedSentiment ? "Re-summarise" : "Summarise"}
          </button>
          {analyzedSentiment && <SentimentBadge sentiment={analyzedSentiment} />}
        </div>
        {error && <p className="alert alert--inline">{error}</p>}
      </div>
    </article>
  );
}
