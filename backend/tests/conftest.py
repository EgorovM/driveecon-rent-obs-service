import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

import app.mail as mail
from app.database import Base, get_db
from app.main import app


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def Session(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture
def db(Session):
    s = Session()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def sent_emails(monkeypatch):
    """Перехватывает отправку почты — реальный SMTP не вызывается."""
    box: list[dict] = []

    def fake_send(to_addr: str, subject: str, body_text: str) -> None:
        box.append({"to": to_addr, "subject": subject, "body": body_text})

    monkeypatch.setattr(mail, "_send", fake_send)
    return box


@pytest.fixture
def client(Session, sent_emails):
    def override_get_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    # Без контекстного менеджера lifespan не запускается (нет seed/планировщика/реальной БД).
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()
