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
    # Канал отправки писем: "auto" (Resend, если задан ключ, иначе SMTP), "resend" или "smtp".
    mail_provider: str = "auto"
    # Resend (HTTP-API, https://resend.com) — отправка по 443 в обход блокировки SMTP.
    resend_api_key: str = ""
    # Адрес отправителя. Для теста подходит onboarding@resend.dev (без своего домена).
    mail_from: str = "Drivee <onboarding@resend.dev>"
    # Проверка PDF-квитанции об оплате через LLM (OpenRouter, https://openrouter.ai).
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    frontend_url: str = "http://localhost:5173"
    api_public_url: str = "http://localhost:8000"
    # Засеять демо-объекты заказчика при пустой БД (для быстрого старта).
    seed_on_start: bool = True
    # Наполнить БД исторической демо-ареной за 2024–2026 (договоры + начисления).
    seed_history: bool = False
    # Владелец объектов по умолчанию (см. DATA.md).
    owner_email: str = "ilpk7778@mail.ru"
    # Вход в админку (один пользователь). Пароль и секрет — только в .env.
    auth_username: str = "admin"
    auth_password: str = ""
    auth_secret: str = ""

    @field_validator("smtp_pass", mode="before")
    @classmethod
    def strip_smtp_pass(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip().rstrip("%")
        return v


settings = Settings()
