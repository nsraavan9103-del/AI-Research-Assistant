"""
Application configuration loaded from .env via pydantic-settings.
All settings are accessible via the global `settings` singleton.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "AI Research Assistant"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # ── Database ─────────────────────────────────────────────────────────────
    # Use SQLite (aiosqlite) by default; swap to postgresql+asyncpg in .env
    DATABASE_URL: str = "sqlite+aiosqlite:///./rag.db"

    # ── JWT / Auth ────────────────────────────────────────────────────────────
    SECRET_KEY: str = "CHANGE_ME_BEFORE_PRODUCTION_USE_256BIT_RANDOM"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    RESET_TOKEN_EXPIRE_MINUTES: int = 15

    # ── File Upload ────────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_DIR: str = "uploads"
    VECTOR_DIR: str = "vector_store"

    # ── Redis (optional – falls back gracefully if not set) ───────────────────
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_ENABLED: bool = False   # Set True when Redis is available

    # ── Celery ────────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    CELERY_ENABLED: bool = False  # Set True when Celery is available

    # ── LLM / Embeddings ──────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "phi3"
    EMBED_MODEL: str = "nomic-embed-text"
    LLM_CACHE_TTL: int = 3600         # seconds
    LLM_CACHE_SIMILARITY: float = 0.95

    # ── Web Search ────────────────────────────────────────────────────────────
    TAVILY_API_KEY: str = ""
    WEB_SEARCH_ENABLED: bool = False

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_FAIL_OPEN: bool = True

    # ── Email (for password reset) ────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@ai-research.app"
    FRONTEND_URL: str = "http://localhost:5173"

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
