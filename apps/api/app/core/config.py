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
    # Signal digest that grounds report suggestions in real relationships (not just
    # column names). Only relationships clearing these thresholds are surfaced, so
    # weak/noisy pairs don't pollute the prompt. Caps bound the prompt size.
    SIGNAL_CORRELATION_MIN: float = 0.4  # |Pearson r| a numeric pair must clear
    SIGNAL_CONTRAST_MIN: float = 1.5  # max/min group-mean ratio a cat→numeric pair must clear
    SIGNAL_SKEW_MIN: float = 2.0  # |skew| above which a numeric column is flagged outlier-heavy
    SIGNAL_MAX_PER_KIND: int = 4  # top-N kept per signal kind (correlations, contrasts, …)
    # Token pricing (USD per 1M tokens) for the active model, used to cost each
    # report. Defaults match gemini-3.5-flash-lite; override if the model changes.
    GEMINI_INPUT_PRICE_PER_1M: float = 0.30
    GEMINI_OUTPUT_PRICE_PER_1M: float = 2.50

    # Security / Auth (JWT). SECRET_KEY MUST be overridden in production via .env.
    SECRET_KEY: str = "dev-secret-change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # --- Email / verification ---------------------------------------------
    # Provider backend for outbound transactional mail:
    #   "console" — log the message + verification link (default; zero setup)
    #   "smtp"    — send via SMTP (use Mailpit locally: host=localhost port=1025)
    #   "resend"  — send via the Resend HTTP API (production)
    EMAIL_PROVIDER: str = "console"
    # Sender identity. EMAIL_FROM must be on a Resend-verified domain in prod.
    EMAIL_FROM: str = "no-reply@visual-ai.local"
    EMAIL_FROM_NAME: str = "Visual AI"
    # Resend API key — required only when EMAIL_PROVIDER=resend.
    RESEND_API_KEY: Optional[SecretStr] = None
    # SMTP config — used only when EMAIL_PROVIDER=smtp (Mailpit dev defaults).
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[SecretStr] = None
    SMTP_USE_TLS: bool = False
    # Public base URL of the Next.js frontend, used to build verification links.
    FRONTEND_URL: str = "http://localhost:3000"
    # How long an email-verification token stays valid.
    EMAIL_VERIFICATION_TOKEN_TTL_HOURS: int = 24
    # Minimum gap between resend-verification requests for one account (seconds).
    EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS: int = 60

    # --- Credits / monetization ------------------------------------------
    # Credits are pegged at ~1 credit ≈ ₹1 (see credit_packs pricing). At a
    # serving cost of ~₹0.65/report this keeps reports cheap for users (~₹10)
    # while retaining ~90%+ gross margin.
    # Credits granted when a user verifies their email (~5 Standard reports).
    SIGNUP_BONUS_CREDITS: int = 50
    # Free/promo credits carry an expiry (shown in UI). NOTE: the auto-expiry
    # sweeper is not yet implemented — this only stamps expires_at for display.
    FREE_CREDIT_TTL_DAYS: int = 30
    # Per-report credit cost by class. The current product generates one report
    # type == "standard"; quick/deep are wired for a future depth selector.
    REPORT_COST_QUICK: int = 5
    REPORT_COST_STANDARD: int = 10
    REPORT_COST_DEEP: int = 20
    # Regeneration reuses the same problem statement, so it's cheaper: cost is
    # original / this divisor, rounded, minimum 1 (e.g. 10 -> 3).
    REPORT_REGEN_DIVISOR: int = 3
    # Datasets at/above this row count cost the large-data multiplier.
    LARGE_DATASET_ROW_THRESHOLD: int = 50_000
    LARGE_DATASET_MULTIPLIER: float = 1.5

    # --- Razorpay ---------------------------------------------------------
    # Key id/secret + webhook-signing secret. Required only to purchase credits.
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[SecretStr] = None
    RAZORPAY_WEBHOOK_SECRET: Optional[SecretStr] = None
    # Currency charged at checkout (credits are the in-app unit everywhere else).
    CREDIT_CURRENCY: str = "inr"
    # Where Razorpay returns the user after payment (payment-link callback).
    PAYMENT_SUCCESS_URL: str = "http://localhost:3000/credits/success"
    PAYMENT_CANCEL_URL: str = "http://localhost:3000/credits"

    # Comma-separated emails allowed to call admin credit endpoints.
    ADMIN_EMAILS: str = ""

    @property
    def admin_emails(self) -> set[str]:
        return {e.strip().lower() for e in self.ADMIN_EMAILS.split(",") if e.strip()}

    # File storage root for uploaded CSVs and their Parquet cache.
    STORAGE_DIR: str = "storage"

    # Max CSV upload size. This is a small-data app (pandas in-memory + DuckDB),
    # so the cap protects the API from OOM on oversized files.
    MAX_UPLOAD_MB: int = 50

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024

    # Cap on raw CSV files per dataset after ZIP expansion. Files are only
    # ingestion inputs — same-schema files are stacked into one table.
    MAX_CSV_FILES: int = 1000

    # Cap on DISTINCT tables after schema clustering. Every table's schema is
    # pasted into the LLM prompts (suggestions, report plans, chat), so this —
    # not the raw file count — bounds prompt size, cost and latency.
    MAX_DATASET_TABLES: int = 50

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
