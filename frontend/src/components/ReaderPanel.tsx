import { useEffect, useState } from "react";

import { api } from "../api/client";
import { formatRelative, safeHref } from "../format";
import type { AnalysisRead, ExtractedArticle, ReaderArticle } from "../types";
import { SentimentBadge } from "./SentimentBadge";

interface Props {
  article: ReaderArticle;
  analysis?: AnalysisRead;
  busy: boolean;
  error?: string;
  onAnalyze: () => void;
  onClose: () => void;
}

type Status = "loading" | "ready" | "error";

const hideBrokenImage = (event: { currentTarget: HTMLImageElement }) => {
  event.currentTarget.style.display = "none";
};

/**
 * Right-side reader. Publishers commonly block iframes, so instead of embedding
 * we fetch the article's main content server-side (reader mode) as ordered
 * text/image blocks. A centered loader shows while it fetches; failures show
 * clear directions (try again / open original) rather than a blank pane.
 */
export function ReaderPanel({ article, analysis, busy, error, onAnalyze, onClose }: Props) {
  const href = safeHref(article.url);
  const [content, setContent] = useState<ExtractedArticle | null>(null);
  const [status, setStatus] = useState<Status>("loading");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setStatus("loading");
    setContent(null);
    api
      .extract(article.url)
      .then((c) => {
        if (active) {
          setContent(c);
          setStatus("ready");
        }
      })
      .catch(() => {
        if (active) setStatus("error");
      });
    return () => {
      active = false;
    };
  }, [article.url, attempt]);

  const hasImages = content?.blocks.some((b) => b.type === "image") ?? false;
  const leadImage = safeHref(article.image_url ?? content?.image);

  return (
    <>
      <div className="reader__scrim" onClick={onClose} />
      <aside className="reader" role="dialog" aria-modal="true" aria-label={article.title}>
        <div className="reader__head">
          <div className="reader__meta">
            <span className="card__source">
              {article.source_name ?? content?.site_name ?? "Source"}
            </span>
            {article.published_at && <span>· {formatRelative(article.published_at)}</span>}
          </div>
          <div className="reader__head-actions">
            {href && (
              <a className="btn btn--ghost btn--small" href={href} target="_blank" rel="noreferrer">
                Open original ↗
              </a>
            )}
            <button className="btn btn--ghost btn--small" onClick={onClose} aria-label="Close reader">
              ✕
            </button>
          </div>
        </div>

        <div className="reader__scroll">
          <div className="reader__brief">
            <h2 className="reader__title">{article.title}</h2>
            {analysis ? (
              <div className="reader__analysis">
                <SentimentBadge sentiment={analysis.sentiment} score={analysis.sentiment_score} />
                <p className="reader__summary">{analysis.summary}</p>
              </div>
            ) : (
              <>
                <button className="btn btn--small" onClick={onAnalyze} disabled={busy}>
                  {busy ? "Summarising…" : "Summarise with AI"}
                </button>
                {error && <p className="alert alert--inline">{error}</p>}
              </>
            )}
          </div>

          <div className="reader__article">
            {status === "loading" && (
              <div className="reader__state">
                <div className="spinner" />
                <p className="reader__state-text">Loading article…</p>
              </div>
            )}

            {status === "error" && (
              <div className="reader__state">
                <span className="reader__state-icon" aria-hidden>
                  📄
                </span>
                <p className="reader__state-title">This article couldn’t be loaded</p>
                <p className="reader__state-text">
                  Some publishers block reader view — it may be paywalled or restrict
                  embedding. Try again, or open the original article.
                </p>
                <div className="reader__state-actions">
                  <button className="btn btn--small" onClick={() => setAttempt((a) => a + 1)}>
                    Try again
                  </button>
                  {href && (
                    <a className="btn btn--ghost btn--small" href={href} target="_blank" rel="noreferrer">
                      Open original ↗
                    </a>
                  )}
                </div>
              </div>
            )}

            {status === "ready" && content && (
              <div className="reader__content">
                {!hasImages && leadImage && (
                  <img className="reader__img" src={leadImage} alt="" onError={hideBrokenImage} />
                )}
                {content.blocks.map((block, i) => {
                  if (block.type === "image") {
                    const src = safeHref(block.value);
                    return src ? (
                      <img
                        key={i}
                        className="reader__img"
                        src={src}
                        alt=""
                        loading="lazy"
                        onError={hideBrokenImage}
                      />
                    ) : null;
                  }
                  return <p key={i}>{block.value}</p>;
                })}
                {href && (
                  <a
                    className="btn btn--ghost btn--small reader__continue"
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Continue on {content.site_name ?? "the original site"} ↗
                  </a>
                )}
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}
