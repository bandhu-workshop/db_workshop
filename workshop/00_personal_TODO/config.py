from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for the application."""

    app_name: str = "Personal TODO"
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = True
    database_url: str = "sqlite:///./database00.db"


settings = Settings()
