import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for the application."""

    APP_NAME: str = "Personal TODO"
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    DEBUG: bool = True
    # DATABASE_URL: str = os.getenv("SQLITE_URL", "sqlite:///./database.db")
    DATABASE_URL: str = os.getenv(
        "POSTGRES_URL",
        "postgresql+psycopg2://admin:admin123@localhost:5432/fastapi_db",
    )
    SKIP_DB_INIT: bool = True  # Add a setting to skip DB initialization if alembic is used for migrations


settings = Settings()
