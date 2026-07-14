import type {
  AnalysisRead,
  ExtractedArticle,
  NewsArticle,
  SearchResponse,
  User,
} from "../types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    // Send the WorkOS session cookie with every request.
    credentials: "include",
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });

  if (!response.ok) {
    let detail = response.statusText;
    let code: string | undefined;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
      code = body.code;
    } catch {
      // Non-JSON error body — fall back to the status text.
    }
    throw new ApiError(detail, response.status, code);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** Build a `?a=1&b=2` query string, dropping undefined/empty params and encoding values. */
function qs(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

export const api = {
  // Auth
  me: () => request<User>("/api/auth/me"),
  logout: () => request<{ logout_url: string }>("/api/auth/logout", { method: "POST" }),
  loginUrl: (screenHint?: string) => `${BASE}/api/auth/login${qs({ screen_hint: screenHint })}`,

  // News discovery
  topHeadlines: (category: string, page = 1, max = 10) =>
    request<SearchResponse>(`/api/news/top-headlines${qs({ category, page, max })}`),
  searchNews: (query: string, page = 1, max = 10) =>
    request<SearchResponse>(`/api/news/search${qs({ q: query, page, max })}`),
  extract: (url: string) => request<ExtractedArticle>(`/api/news/extract${qs({ url })}`),

  // Summaries (scoped to the signed-in user)
  analyze: (article: NewsArticle) =>
    request<AnalysisRead>("/api/analyses", {
      method: "POST",
      body: JSON.stringify({ article }),
    }),
  listAnalyses: (limit: number, offset: number, q?: string) =>
    request<AnalysisRead[]>(`/api/analyses${qs({ limit, offset, q })}`),
  deleteAnalysis: (id: string) => request<void>(`/api/analyses/${id}`, { method: "DELETE" }),
};

export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}
