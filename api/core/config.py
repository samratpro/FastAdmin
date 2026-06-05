from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    # Server
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "change-me-in-production"

    # Database — only sqlite and postgresql are supported
    DB_ENGINE: str = "sqlite"
    DB_PATH: str = "./db.sqlite3"
    DATABASE_URL: str = ""

    # Email
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_SECURE: bool = False
    EMAIL_USER: str = ""
    EMAIL_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@example.com"

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_EXPIRES_IN: str = "1d"
    JWT_REFRESH_EXPIRES_IN: str = "7d"

    # URLs / CORS
    FRONTEND_URL: str = "http://localhost:3000"
    ADMIN_URL: str = "http://localhost:7000"
    CORS_ORIGIN: str = "http://localhost:7000,http://127.0.0.1:7000,http://localhost:3000,http://localhost:8000"
    NEXTJS_SITE_URL: str = ""
    REVALIDATE_SECRET: str = ""
    SITE_URL: str = ""

    # Persistent data directory for backup schedule/log/drive credentials.
    # In Docker this is set to /app/appdata (mounted as a host volume).
    # In development it defaults to "" which means the api/ root is used.
    DATA_DIR: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGIN.split(",") if o.strip()]


settings = Settings()
