import os
from typing import Optional
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    ENV: str = "development"
    PROJECT_NAME: str = "Visual AI Data Analyst"
    API_V1_STR: str = "/api/v1"

    # Database Settings
    # We load this from environment variables. If running in Docker, it uses the compose db.
    DATABASE_URL: str

    # AI Provider API Keys (Make optional for now)
    GOOGLE_API_KEY: Optional[SecretStr] = None
    # Default Gemini model. flash-lite is ~70% cheaper than flash ($0.30/$2.50 vs
    # $1.50/$9.00 per 1M tokens) and still supports function calling + structured
    # output + 1M context, which is all the agent needs. Bump to gemini-3.5-flash
    # if report reasoning ever slips.
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    # Max ReAct steps (model <-> tool round-trips) before LangGraph aborts.
    # Guards against the agent looping on a hard question.
    AGENT_RECURSION_LIMIT: int = 50
    # Retries (with exponential backoff) for transient LLM errors — 503 model
    # overload, 429 rate limits, 500s. Set to 0 to fail fast.
    LLM_MAX_RETRIES: int = 3
    # Token pricing (USD per 1M tokens) for the active model, used to cost each
    # report. Defaults match gemini-3.5-flash-lite; override if the model changes.
    GEMINI_INPUT_PRICE_PER_1M: float = 0.30
    GEMINI_OUTPUT_PRICE_PER_1M: float = 2.50

    # Security / Auth (JWT). SECRET_KEY MUST be overridden in production via .env.
    SECRET_KEY: str = "dev-secret-change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # File storage root for uploaded CSVs and their Parquet cache.
    STORAGE_DIR: str = "storage"

    # Max CSV upload size. This is a small-data app (pandas in-memory + DuckDB),
    # so the cap protects the API from OOM on oversized files.
    MAX_UPLOAD_MB: int = 50

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024

    # CORS origins for the Next.js frontend (comma-separated list in the .env).
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        """Parse the comma-separated CORS origins string into a list."""
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]

    # SettingsConfigDict tells Pydantic to read from a .env file if it exists.
    # case_sensitive=True means Env variables must match setting properties exactly (e.g. ENV).
    # extra="ignore" ignores extra variables in the .env that are not specified in this class.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Instantiate settings so it can be imported and shared across the codebase
settings = Settings()
