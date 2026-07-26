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
    # Only chat mode still runs the ReAct loop (reports are now single-shot), so
    # this caps an interactive turn. Kept modest to bound the worst-case cost of
    # a confused turn — 12 round-trips is ample for any real question.
    AGENT_RECURSION_LIMIT: int = 12
    # Retries (with exponential backoff) for transient LLM errors — 503 model
    # overload, 429 rate limits, 500s. Set to 0 to fail fast.
    LLM_MAX_RETRIES: int = 3
    # Thinking-token budget. Our tasks reason deterministically in Python, so we
    # want thinking minimal. NOTE: Gemini-3 models (e.g. gemini-3.5-flash-lite)
    # REJECT 0 with a 400 — the lowest valid disable is a small positive cap.
    # Values: a low int caps reasoning cost; -1 = dynamic/auto; None = don't send
    # (use the model default, safest if you switch to a model with a higher min).
    LLM_THINKING_BUDGET: int | None = 128
    # Hard caps on generated output tokens. Unbounded output is both a cost and a
    # verbosity risk; these are generous ceilings, not targets. The section cap is
    # sized for a rich ~120-180 word paragraph; the plan cap must fit the whole
    # plan JSON (summary + up to 6 sections + recommendations).
    REPORT_SECTION_MAX_OUTPUT_TOKENS: int = 1024
    REPORT_PLAN_MAX_OUTPUT_TOKENS: int = 2048
    SUGGESTION_MAX_OUTPUT_TOKENS: int = 700
    CHAT_MAX_OUTPUT_TOKENS: int = 2048
    # Chat sends recent history back on every turn; cap it so a long session
    # can't grow the per-turn context (and cost) without bound.
    CHAT_HISTORY_MAX_MESSAGES: int = 12
    # Deterministic analysis-battery limits: how many findings/charts to compute
    # before the (single) LLM plan pass. Broad enough for a varied, multi-section
    # report; the plan curates the most goal-relevant subset.
    ANALYSIS_MAX_FINDINGS: int = 18
    ANALYSIS_MAX_CHARTS: int = 14
    # Charts shown in any one report section — keeps them spread out, not piled up.
    REPORT_MAX_CHARTS_PER_SECTION: int = 3
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
