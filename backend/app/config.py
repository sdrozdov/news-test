"""Application configuration, loaded from environment variables / .env files."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings.

    Every value has a sensible default so the app can boot for local development
    without a fully-populated environment. External integrations degrade
    gracefully (a clear 503) when their keys are missing rather than crashing.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "AI News"
    # Comma-separated list of allowed browser origins for CORS.
    cors_origins: str = "http://localhost:5173,http://localhost:4173"
    # Create tables on startup. Handy for dev; disable in prod and run migrations.
    auto_create_tables: bool = True

    # --- Database ---
    # Accepts a standard postgres URL (postgresql://...) or an async one
    # (postgresql+asyncpg://...). libpq-only params like ?sslmode=require are
    # handled transparently. Defaults to the local docker-compose Postgres.
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/newsai"
    db_echo: bool = False
    # Use NullPool (no connection pooling) — recommended on serverless platforms.
    db_use_null_pool: bool = False

    # --- News provider (GNews) ---
    gnews_api_key: str = ""
    gnews_base_url: str = "https://gnews.io/api/v4"
    news_default_lang: str = "en"
    news_default_max: int = 10

    # --- OpenAI ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-nano"
    openai_base_url: str | None = None
    # Budget: timeout * (max_retries + 1) is the worst-case wall time for one
    # analysis. Keep it comfortably under any serverless request ceiling.
    openai_timeout_seconds: float = 20.0
    openai_max_retries: int = 1
    openai_temperature: float = 0.0
    # Cap input chars sent to, and output tokens requested from, the model to
    # keep requests cheap and bounded.
    ai_max_input_chars: int = 6000
    ai_max_output_tokens: int = 500

    # --- Auth (WorkOS AuthKit) ---
    # When these are unset the app runs in local "dev mode": no login is required
    # and all data belongs to a single local user. Set all three to enable auth.
    workos_api_key: str = ""
    workos_client_id: str = ""
    # Encrypts the session cookie; must be >= 32 chars (e.g. `openssl rand -base64 32`).
    workos_cookie_password: str = ""
    # AuthKit redirects here after sign-in (must be registered in WorkOS).
    workos_redirect_uri: str = "http://localhost:5173/api/auth/callback"
    # Where to send the browser after login/logout — the SPA origin.
    app_base_url: str = "http://localhost:5173"
    # Set True behind HTTPS so the session cookie is only sent over TLS.
    session_cookie_secure: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def auth_enabled(self) -> bool:
        """Auth is active only when all WorkOS settings are present."""
        return bool(
            self.workos_api_key and self.workos_client_id and self.workos_cookie_password
        )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton (import-safe)."""
    return Settings()
