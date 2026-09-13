from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str = "000000:changeme"
    bot_username: str = ""
    webapp_url: str = "http://localhost:8080"
    database_url: str = "postgresql://goal:goal@postgres:5432/goaltracker"
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 168
    owner_telegram_id: int = 1001
    demo_mode: bool = True
    skip_seed: bool = False
    upload_dir: Path = Path("/data/uploads")
    max_upload_bytes: int = 25 * 1024 * 1024


settings = Settings()
