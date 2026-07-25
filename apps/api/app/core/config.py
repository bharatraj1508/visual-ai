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
    # Default Gemini model used by the agent. flash is cheap/fast; swap to -pro for harder analysis.
    GEMINI_MODEL: str = "gemini-3.5-flash"
    # Max ReAct steps (model <-> tool round-trips) before LangGraph aborts.
    # Guards against the agent looping on a hard question.
    AGENT_RECURSION_LIMIT: int = 50

    # Security / Auth (JWT). SECRET_KEY MUST be overridden in production via .env.
    SECRET_KEY: str = "dev-secret-change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # File storage root for uploaded CSVs and their Parquet cache.
    STORAGE_DIR: str = "storage"

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
