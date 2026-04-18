from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str = "postgresql+psycopg://drivee:drivee@localhost:5432/drivee"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    """Gmail: обычно 587 + STARTTLS. Если таймауты — попробуйте SMTP_PORT=465 и SMTP_USE_SSL=true."""
    smtp_use_ssl: bool = False
    """True = порт 465, сразу SSL (часто проходит там, где режут STARTTLS на 587)."""
    smtp_force_ipv4: bool = True
    """По умолчанию True: только IPv4 (часто устраняет зависания на битом IPv6)."""
    smtp_timeout: int = 30
    smtp_debug: bool = False
    frontend_url: str = "http://localhost:5173"
    api_public_url: str = "http://localhost:8000"

    @field_validator("smtp_pass", mode="before")
    @classmethod
    def strip_smtp_pass(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip().rstrip("%")
        return v


settings = Settings()
