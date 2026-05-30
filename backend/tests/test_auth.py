"""ФТ: вход по логину/паролю и защита эндпоинтов токеном."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import auth
from app.config import settings
from app.main import app


@pytest.fixture
def creds(monkeypatch):
    monkeypatch.setattr(settings, "auth_username", "admin")
    monkeypatch.setattr(settings, "auth_password", "secret123")
    monkeypatch.setattr(settings, "auth_secret", "unit-test-secret")


def test_protected_requires_token(creds):
    # require_auth выполняется раньше обработчика (до обращения к БД).
    c = TestClient(app)
    assert c.get("/api/properties").status_code == 401
    assert c.post("/api/jobs/run-now").status_code == 401


def test_login_wrong_password(creds):
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    assert r.status_code == 401


def test_login_ok_and_token_accepted(creds):
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    assert r.status_code == 200
    token = r.json()["token"]
    assert r.json()["username"] == "admin"

    # Валидный токен пропускается зависимостью, чужой — отклоняется.
    auth.require_auth(authorization=f"Bearer {token}")
    with pytest.raises(HTTPException):
        auth.require_auth(authorization="Bearer wrong")
    with pytest.raises(HTTPException):
        auth.require_auth(authorization=None)


def test_public_endpoints_open(creds):
    c = TestClient(app)
    # health и вход доступны без токена (login без тела → 422 валидации, не 401).
    assert c.get("/api/health").status_code == 200
    assert c.post("/api/auth/login", json={}).status_code == 422
