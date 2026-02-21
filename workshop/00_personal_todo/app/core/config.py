from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for the application."""

    APP_NAME: str = "Personal TODO"
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./database.db"
    SKIP_DB_INIT: bool = True  # Add a setting to skip DB initialization if alembic is used for migrations


settings = Settings()
