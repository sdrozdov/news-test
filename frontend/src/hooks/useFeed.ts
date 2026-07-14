import { useCallback, useRef, useState } from "react";

import { api, errorMessage } from "../api/client";
import type { NewsArticle } from "../types";

export type FeedMode =
  | { kind: "category"; category: string }
  | { kind: "search"; query: string };

const BATCH = 10; // articles per page / per "Load more"

// Dedup key mirroring the backend: lowercase, ignore punctuation/spacing, so the
// same story from two URLs (or re-served on a later page) is only shown once.
const titleKey = (title: string | null | undefined) =>
  (title ?? "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();

/**
 * The briefing feed: 10 articles to start, "Load more" fetches the next page and
 * appends (deduped). A request-id guard drops out-of-order responses so a slow
 * earlier fetch can't overwrite a newer one.
 */
export function useFeed() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<FeedMode>({ kind: "category", category: "general" });
  const [hasMore, setHasMore] = useState(false);
  const pageRef = useRef(1);
  const seen = useRef<{ urls: Set<string>; titles: Set<string> }>({
    urls: new Set(),
    titles: new Set(),
  });
  const reqId = useRef(0);
  const inFlight = useRef(false);

  const fetchPage = useCallback(async (m: FeedMode, page: number, append: boolean) => {
    const myReq = ++reqId.current;
    inFlight.current = true;
    setLoading(true);
    if (!append) {
      setError(null);
      setArticles([]);
      seen.current = { urls: new Set(), titles: new Set() };
    }
    try {
      const result =
        m.kind === "category"
          ? await api.topHeadlines(m.category, page, BATCH)
          : await api.searchNews(m.query, page, BATCH);
      if (myReq !== reqId.current) return; // superseded by a newer request
      const fresh = result.articles.filter((a) => {
        const t = titleKey(a.title);
        return !seen.current.urls.has(a.url) && !(t && seen.current.titles.has(t));
      });
      fresh.forEach((a) => {
        seen.current.urls.add(a.url);
        const t = titleKey(a.title);
        if (t) seen.current.titles.add(t);
      });
      setArticles((prev) => (append ? [...prev, ...fresh] : fresh));
      // Offer "Load more" whenever the last fetch returned something new — same
      // rule for category and search. (The old `>= BATCH` gate hid the button on
      // search, whose responses often come back under 10 after the provider's
      // dedup.) When a fetch yields nothing new, the next page is dry, so hide it.
      setHasMore(fresh.length > 0);
      pageRef.current = page; // only advance on success, so a failed retry re-fetches it
    } catch (err) {
      if (myReq !== reqId.current) return;
      // Surface the error; on "Load more" keep hasMore so the button stays for a
      // retry instead of silently vanishing as if the feed were exhausted.
      setError(errorMessage(err, "Could not load headlines."));
      if (!append) {
        setArticles([]);
        setHasMore(false);
      }
    } finally {
      inFlight.current = false;
      if (myReq === reqId.current) setLoading(false);
    }
  }, []);

  const loadCategory = useCallback(
    (category: string) => {
      const m: FeedMode = { kind: "category", category };
      setMode(m);
      pageRef.current = 1;
      void fetchPage(m, 1, false);
    },
    [fetchPage],
  );

  const search = useCallback(
    (query: string) => {
      // An empty submit returns to the top-headlines feed rather than doing nothing.
      const q = query.trim();
      const m: FeedMode = q
        ? { kind: "search", query: q }
        : { kind: "category", category: "general" };
      setMode(m);
      pageRef.current = 1;
      void fetchPage(m, 1, false);
    },
    [fetchPage],
  );

  const loadMore = useCallback(() => {
    // Ignore a double-click while a fetch is still running, so the same page
    // isn't requested twice before the button's disabled state re-renders.
    if (inFlight.current) return;
    void fetchPage(mode, pageRef.current + 1, true);
  }, [fetchPage, mode]);

  return { articles, loading, error, mode, hasMore, loadCategory, search, loadMore };
}
