"""Простая авторизация по логину/паролю (один пользователь-владелец).

Логин/пароль/секрет берутся из окружения (.env): AUTH_USERNAME, AUTH_PASSWORD,
AUTH_SECRET. После входа выдаётся stateless-токен (HMAC от логина на секрете) —
он не хранится на сервере, переживает рестарт и проверяется на каждый запрос.
"""

import hashlib
import hmac

from fastapi import APIRouter, Header, HTTPException

from app.config import settings
from app.schemas import LoginBody, TokenOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _expected_token() -> str:
    secret = settings.auth_secret or settings.auth_password
    return hmac.new(secret.encode(), settings.auth_username.encode(), hashlib.sha256).hexdigest()


def _check_credentials(username: str, password: str) -> bool:
    ok_user = hmac.compare_digest(username, settings.auth_username)
    ok_pass = bool(settings.auth_password) and hmac.compare_digest(password, settings.auth_password)
    return ok_user and ok_pass


@router.post("/login", response_model=TokenOut)
def login(body: LoginBody):
    if not settings.auth_password:
        raise HTTPException(503, "Авторизация не настроена: задайте AUTH_PASSWORD")
    if not _check_credentials(body.username, body.password):
        raise HTTPException(401, "Неверный логин или пароль")
    return TokenOut(token=_expected_token(), username=settings.auth_username)


def require_auth(authorization: str | None = Header(default=None)) -> None:
    """Зависимость: пропускает запрос только с валидным Bearer-токеном."""
    if not settings.auth_password:
        # Авторизация не настроена — не блокируем (для локальной разработки).
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Требуется авторизация")
    token = authorization[len("Bearer "):]
    if not hmac.compare_digest(token, _expected_token()):
        raise HTTPException(401, "Недействительный токен, войдите заново")
