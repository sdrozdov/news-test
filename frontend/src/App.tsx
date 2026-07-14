import { useEffect, useState } from "react";

import { ArticleCard } from "./components/ArticleCard";
import { EmptyState } from "./components/EmptyState";
import { ReaderPanel } from "./components/ReaderPanel";
import { SavedList } from "./components/SavedList";
import { SearchBar } from "./components/SearchBar";
import { SignIn } from "./components/SignIn";
import { TopBar, type Tab } from "./components/TopBar";
import { TopicChips } from "./components/TopicChips";
import { useAnalyses } from "./hooks/useAnalyses";
import { useAuth } from "./hooks/useAuth";
import { useFeed } from "./hooks/useFeed";
import { CATEGORIES } from "./types";
import type { ReaderArticle, User } from "./types";

export default function App() {
  const auth = useAuth();

  if (auth.loading) {
    return (
      <div className="splash">
        <div className="spinner" aria-label="Loading" />
      </div>
    );
  }

  if (!auth.user) {
    return (
      <SignIn
        onSignIn={() => auth.login("sign-in")}
        onSignUp={() => auth.login("sign-up")}
        error={auth.error}
      />
    );
  }

  return <Briefing user={auth.user} onSignOut={auth.logout} />;
}

function Briefing({ user, onSignOut }: { user: User; onSignOut: () => void }) {
  const feed = useFeed();
  const analyses = useAnalyses();
  const [tab, setTab] = useState<Tab>("briefing");
  const [selected, setSelected] = useState<ReaderArticle | null>(null);

  useEffect(() => {
    void feed.loadCategory("general");
    void analyses.refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activeCategory = feed.mode.kind === "category" ? feed.mode.category : null;

  return (
    <div className="app">
      <TopBar user={user} tab={tab} onTab={setTab} onSignOut={onSignOut} />

      {tab === "briefing" ? (
        <main className="feed">
          <div className="feed__controls">
            <TopicChips categories={CATEGORIES} active={activeCategory} onSelect={feed.loadCategory} />
            <SearchBar onSearch={feed.search} loading={feed.loading} />
          </div>

          {feed.mode.kind === "search" && (
            <p className="feed__note">
              Results for “<strong>{feed.mode.query}</strong>”
            </p>
          )}
          {feed.error && <p className="alert">{feed.error}</p>}

          <div className="grid">
            {feed.loading && feed.articles.length === 0 && (
              <EmptyState icon="⏳" text="Loading headlines…" />
            )}
            {!feed.loading && !feed.error && feed.articles.length === 0 && (
              <EmptyState icon="🔍" text="No articles found. Try another topic or search." />
            )}
            {feed.articles.map((article) => (
              <ArticleCard
                key={article.url}
                article={article}
                analyzedSentiment={analyses.byUrl.get(article.url)?.sentiment}
                busy={analyses.analyzing.has(article.url)}
                error={analyses.analyzeErrors.get(article.url)}
                onAnalyze={() => analyses.analyze(article)}
                onOpen={() => setSelected(article)}
              />
            ))}
          </div>
          {feed.hasMore && (
            <div className="loadmore">
              <button className="btn btn--ghost" onClick={feed.loadMore} disabled={feed.loading}>
                {feed.loading ? "Loading…" : "Load more"}
              </button>
            </div>
          )}
        </main>
      ) : (
        <main className="feed">
          {analyses.error && <p className="alert">{analyses.error}</p>}
          <SavedList
            items={analyses.items}
            page={analyses.page}
            hasMore={analyses.hasMore}
            loading={analyses.loading}
            query={analyses.query}
            onSearch={analyses.search}
            onPrev={analyses.prevPage}
            onNext={analyses.nextPage}
            onDelete={analyses.remove}
            onOpen={(article) => setSelected(article)}
          />
        </main>
      )}

      {selected && (
        <ReaderPanel
          article={selected}
          analysis={analyses.byUrl.get(selected.url)}
          busy={analyses.analyzing.has(selected.url)}
          error={analyses.analyzeErrors.get(selected.url)}
          onAnalyze={() => analyses.analyze(selected)}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
