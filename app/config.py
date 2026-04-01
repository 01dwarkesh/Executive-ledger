from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    from_email: str = "noreply@example.com"
    frontend_url: str = "http://localhost:3000"
    upload_dir: str = "uploads"

    # SMTP (aiosmtplib)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: bool = True

    model_config = {"env_file": str(ENV_FILE), "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
