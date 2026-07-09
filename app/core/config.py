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
