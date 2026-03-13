import os
import httpx
import json
from typing import Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Bootstrap settings for Params Store
    PARAMS_STORE_URL: str
    APP_NAME: str

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    JWT_EXPIRY_HOURS: int
    FRONTEND_ORIGIN: str

    # LLM Mode and Docker settings
    # Options: "local" (Mac — uses local Ollama at localhost:11434),
    #          "docker" (uses dockerized Ollama at ollama:11434),
    #          "gemini" (uses Google Gemini API)
    LLM_MODE: str
    DOCKER_COMPOSE_PATH: str
    DOCKER_COMPOSE_PROJECT: str

    # RAG / vector store
    EMBEDDING_MODEL_NAME: str
    LLM_MODEL_NAME: str = ""
    OLLAMA_BASE_URL: str = ""
    SIMILARITY_THRESHOLD: float

    # File storage
    FILE_STORAGE_ROOT: str

    # UUID masking (AES-256 key as 64-char hex)
    UUID_MASK_KEY: str

    # Email (Gmail SMTP)
    GMAIL_SENDER_EMAIL: str = ""
    GMAIL_APP_PASSWORD: str = ""
    GMAIL_SMTP_SERVER: str = "smtp.gmail.com"
    GMAIL_SMTP_PORT: int = 587

    # Gemini settings (used when LLM_MODE="gemini")
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = ""

    # Logging
    LOG_LEVEL: str

    # File upload settings
    MAX_UPLOAD_SIZE: int
    MAX_FILES_PER_UPLOAD: int
    ALLOWED_EXTENSIONS: list[str]

    @property
    def pgvector_connection_string(self) -> str:
        """Sync psycopg3 connection string for langchain_postgres.PGVector."""
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg")

    def __init__(self, **values: Any) -> None:
        merged_values: dict[str, Any] = dict(values)

        params_store_url = os.environ.get("PARAMS_STORE_URL")

        if params_store_url:
            try:
                response = httpx.get(f"{params_store_url}", timeout=5.0)
                if response.status_code == 200:
                    remote_settings = response.json()
                    # Only add if not already passed in explicitly
                    for key, value in remote_settings.items():
                        if key not in merged_values:
                            # If the value is a string and should be a list, parse it
                            if isinstance(value, str) and (value.startswith("[") or value.startswith("{")):
                                try:
                                    value = json.loads(value)
                                except Exception:
                                    pass
                            merged_values[key] = value
                else:
                    print(f"Warning: Params Store returned status {response.status_code}")
            except Exception as e:
                print(f"Warning: Could not fetch settings from Params Store: {e}")

        if "OLLAMA_BASE_URL" not in merged_values and not os.environ.get("OLLAMA_BASE_URL"):
            llm_mode = merged_values.get("LLM_MODE") or os.environ.get("LLM_MODE", "docker")
            if llm_mode == "local":
                merged_values["OLLAMA_BASE_URL"] = "http://localhost:11434"
            elif llm_mode != "gemini":
                merged_values["OLLAMA_BASE_URL"] = "http://ollama:11434"

        super().__init__(**merged_values)


settings = Settings()
