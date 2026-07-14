import { useCallback, useRef, useState } from "react";

import { api, errorMessage } from "../api/client";
import type { AnalysisRead, NewsArticle } from "../types";

const PAGE_SIZE = 10;

export function useAnalyses() {
  const [items, setItems] = useState<AnalysisRead[]>([]); // current Saved page
  const [byUrl, setByUrl] = useState<Map<string, AnalysisRead>>(new Map()); // for inline badges/reader
  const [page, setPage] = useState(0);
  const [query, setQuery] = useState("");
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Per-article state, so many summaries can run at once with independent status.
  const [analyzing, setAnalyzing] = useState<Set<string>>(new Set());
  const [analyzeErrors, setAnalyzeErrors] = useState<Map<string, string>>(new Map());
  const reqId = useRef(0);

  const loadPage = useCallback(async (p: number, q: string) => {
    const myReq = ++reqId.current;
    setLoading(true);
    setError(null);
    try {
      // Fetch one extra row to tell whether a next page exists — accurate even
      // when the total is an exact multiple of PAGE_SIZE (no phantom empty page).
      const results = await api.listAnalyses(PAGE_SIZE + 1, p * PAGE_SIZE, q || undefined);
      if (myReq !== reqId.current) return; // superseded by a newer load (fast typing / paging)
      const pageItems = results.slice(0, PAGE_SIZE);
      // Auto-recover from an empty page past the first (e.g. the last row on a
      // page>0 was just deleted) by stepping back a page.
      if (pageItems.length === 0 && p > 0) {
        void loadPage(p - 1, q);
        return;
      }
      setItems(pageItems);
      setPage(p);
      setHasMore(results.length > PAGE_SIZE);
      setByUrl((prev) => {
        const next = new Map(prev);
        for (const r of pageItems) next.set(r.article.url, r);
        return next;
      });
    } catch (err) {
      if (myReq !== reqId.current) return;
      setError(errorMessage(err, "Could not load saved summaries."));
    } finally {
      if (myReq === reqId.current) setLoading(false);
    }
  }, []);

  const refresh = useCallback(() => loadPage(0, ""), [loadPage]);
  const search = useCallback(
    (q: string) => {
      setQuery(q);
      void loadPage(0, q);
    },
    [loadPage],
  );
  const nextPage = useCallback(() => loadPage(page + 1, query), [loadPage, page, query]);
  const prevPage = useCallback(() => {
    if (page > 0) void loadPage(page - 1, query);
  }, [loadPage, page, query]);

  const analyze = useCallback(
    async (article: NewsArticle) => {
      setAnalyzing((prev) => new Set(prev).add(article.url));
      setAnalyzeErrors((prev) => {
        const next = new Map(prev);
        next.delete(article.url);
        return next;
      });
      try {
        const result = await api.analyze(article);
        // Match on the server-canonical url (it may differ from the input, e.g.
        // trimmed) so a re-summarise updates in place rather than duplicating.
        const url = result.article.url;
        setByUrl((prev) => new Map(prev).set(url, result));
        setItems((prev) => {
          // A re-summarise of a row already on screen (any page/filter): update it
          // in place so its summary + sentiment refresh.
          if (prev.some((r) => r.article.url === url)) {
            return prev.map((r) => (r.article.url === url ? result : r));
          }
          // A brand-new summary only belongs at the top of the unfiltered first
          // page; cap at PAGE_SIZE so the page doesn't overflow into the next.
          if (page === 0 && !query) return [result, ...prev].slice(0, PAGE_SIZE);
          return prev;
        });
      } catch (err) {
        const message = errorMessage(err, "Summarising failed.");
        setAnalyzeErrors((prev) => new Map(prev).set(article.url, message));
      } finally {
        setAnalyzing((prev) => {
          const next = new Set(prev);
          next.delete(article.url);
          return next;
        });
      }
    },
    [page, query],
  );

  const remove = useCallback(
    async (id: string) => {
      setError(null);
      const target = items.find((r) => r.id === id);
      setItems((prev) => prev.filter((r) => r.id !== id)); // optimistic
      if (target) {
        setByUrl((prev) => {
          const next = new Map(prev);
          next.delete(target.article.url);
          return next;
        });
      }
      try {
        await api.deleteAnalysis(id);
        void loadPage(page, query); // reconcile: backfill the row (steps back if emptied)
      } catch (err) {
        // Reconcile against the server (the row reappears in its true position if
        // the delete didn't happen), then surface the error last so the reload
        // doesn't clear it.
        await loadPage(page, query);
        if (target) setByUrl((prev) => new Map(prev).set(target.article.url, target));
        setError(errorMessage(err, "Delete failed. Please try again."));
      }
    },
    [items, loadPage, page, query],
  );

  return {
    items,
    byUrl,
    page,
    query,
    hasMore,
    loading,
    error,
    analyzing,
    analyzeErrors,
    refresh,
    search,
    nextPage,
    prevPage,
    analyze,
    remove,
  };
}
