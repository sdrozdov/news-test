// Mirrors the backend Pydantic schemas (app/schemas).

export type Sentiment = "positive" | "neutral" | "negative";

export interface User {
  id: string;
  email?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  profile_picture_url?: string | null;
}

export interface NewsArticle {
  title: string;
  description?: string | null;
  content?: string | null;
  url: string;
  image_url?: string | null;
  source_name?: string | null;
  published_at?: string | null;
}

export interface SearchResponse {
  query: string;
  count: number;
  articles: NewsArticle[];
}

export interface ArticleRead {
  id: string;
  url: string;
  title: string;
  description?: string | null;
  image_url?: string | null;
  source_name?: string | null;
  published_at?: string | null;
}

export interface AnalysisRead {
  id: string;
  summary: string;
  sentiment: Sentiment;
  sentiment_score: number;
  model: string;
  created_at: string;
  updated_at: string;
  article: ArticleRead;
}

export interface Category {
  key: string;
  label: string;
}

// Briefing feed topics — keys are GNews top-headlines categories.
export const CATEGORIES: Category[] = [
  { key: "general", label: "Top" },
  { key: "world", label: "World" },
  { key: "nation", label: "Nation" },
  { key: "business", label: "Business" },
  { key: "technology", label: "Technology" },
  { key: "science", label: "Science" },
  { key: "health", label: "Health" },
  { key: "sports", label: "Sports" },
  { key: "entertainment", label: "Entertainment" },
];

// Minimal article shape the reader panel needs — satisfied by both a live
// NewsArticle and a saved ArticleRead.
export interface ReaderArticle {
  title: string;
  url: string;
  description?: string | null;
  image_url?: string | null;
  source_name?: string | null;
  published_at?: string | null;
}

export interface ArticleBlock {
  type: "text" | "image";
  value: string;
}

export interface ExtractedArticle {
  url: string;
  title?: string | null;
  author?: string | null;
  image?: string | null;
  site_name?: string | null;
  blocks: ArticleBlock[];
}
