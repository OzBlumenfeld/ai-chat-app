from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    JWT_EXPIRY_HOURS: int
    FRONTEND_ORIGIN: str

    # LLM Mode and Docker settings
    LLM_MODE: str
    DOCKER_COMPOSE_PATH: str
    DOCKER_COMPOSE_PROJECT: str

    # RAG / vector store
    CHROMA_HOST: str
    CHROMA_PORT: str
    COLLECTION_NAME: str
    EMBEDDING_MODEL_NAME: str
    LLM_MODEL_NAME: str
    OLLAMA_BASE_URL: str
    SIMILARITY_THRESHOLD: float

    # File storage
    FILE_STORAGE_ROOT: str

    # UUID masking (AES-256 key as 64-char hex)
    UUID_MASK_KEY: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Email (Gmail SMTP)
    GMAIL_SENDER_EMAIL: str = ""
    GMAIL_APP_PASSWORD: str = ""
    GMAIL_SMTP_SERVER: str = "smtp.gmail.com"
    GMAIL_SMTP_PORT: int = 587

    # Gemini settings (used when LLM_MODE="gemini")
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Logging
    LOG_LEVEL: str

    # File upload settings
    MAX_UPLOAD_SIZE: int
    MAX_FILES_PER_UPLOAD: int
    ALLOWED_EXTENSIONS: list[str]


settings = Settings()
