"""ФТ: проверки API через TestClient (с замоканным SMTP)."""

import uuid
from datetime import date


def _new_property(client, **over):
    payload = {
        "name": "Кирова, 1 этаж",
        "address": "г. Якутск, ул. Кирова",
        "status": "free",
        "owner_email": "owner@example.com",
    }
    payload.update(over)
    r = client.post("/api/properties", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def _lease_payload(**over):
    today = date.today()
    payload = {
        "tenant_name": "ИП Иванов",
        "tenant_email": "ivanov@mail.ru",
        "rent_start": today.replace(day=1).isoformat(),
        "rent_end": today.replace(year=today.year + 1, day=28).isoformat(),
        "rent_amount": 35000,
        "payment_day": 17,
    }
    payload.update(over)
    return payload


# --- ФТ-1: CRUD объектов ---

def test_property_crud(client):
    p = _new_property(client)
    pid = p["id"]

    assert client.get("/api/properties").json()[0]["id"] == pid
    assert client.get(f"/api/properties/{pid}").json()["name"] == "Кирова, 1 этаж"

    r = client.patch(f"/api/properties/{pid}", json={"status": "listed_ykt"})
    assert r.json()["status"] == "listed_ykt"

    assert client.delete(f"/api/properties/{pid}").json() == {"ok": True}
    assert client.get(f"/api/properties/{pid}").status_code == 404


def test_property_invalid_email_422(client):
    r = client.post(
        "/api/properties",
        json={"name": "x", "address": "y", "owner_email": "not-an-email"},
    )
    assert r.status_code == 422


# --- ФТ-2: аренда создаёт ежемесячные начисления ---

def test_create_lease_generates_periods(client):
    p = _new_property(client)
    r = client.post(f"/api/properties/{p['id']}/leases", json=_lease_payload())
    assert r.status_code == 200, r.text
    lease = r.json()
    assert lease["rent_amount"] == 35000
    assert lease["payment_day"] == 17
    assert len(lease["periods"]) >= 1
    first = lease["periods"][0]
    assert first["amount_due"] == 35000
    assert first["status"] == "pending"
    # Объект становится занятым.
    assert client.get(f"/api/properties/{p['id']}").json()["status"] == "occupied"


def test_create_lease_end_before_start_422(client):
    p = _new_property(client)
    r = client.post(
        f"/api/properties/{p['id']}/leases",
        json=_lease_payload(rent_start="2026-05-01", rent_end="2026-04-01"),
    )
    assert r.status_code == 422


# --- ФТ-3: загрузка .txt ---

def test_lease_upload_txt(client):
    p = _new_property(client)
    txt = (
        "ФИО: Петров Сергей\n"
        "Email: sergey@yandex.ru\n"
        "Дата начала аренды: 01.03.2026\n"
        "Дата окончания: 31.08.2026\n"
        "Сумма аренды: 30000\n"
        "День оплаты: 4\n"
    )
    r = client.post(
        f"/api/properties/{p['id']}/leases/upload",
        files={"file": ("lease.txt", txt.encode("utf-8"), "text/plain")},
    )
    assert r.status_code == 200, r.text
    lease = r.json()
    assert lease["tenant_email"] == "sergey@yandex.ru"
    assert lease["rent_amount"] == 30000
    assert lease["payment_day"] == 4


def test_lease_upload_missing_fields_400(client):
    p = _new_property(client)
    txt = "ФИО: Без Суммы\nEmail: x@mail.ru\n"
    r = client.post(
        f"/api/properties/{p['id']}/leases/upload",
        files={"file": ("bad.txt", txt.encode("utf-8"), "text/plain")},
    )
    assert r.status_code == 400


# --- ФТ-4: фиксация оплаты (частичная и полная) ---

def test_record_payment_partial_then_full(client, sent_emails):
    p = _new_property(client)
    lease = client.post(f"/api/properties/{p['id']}/leases", json=_lease_payload()).json()
    period = lease["periods"][0]
    base = f"/api/properties/{p['id']}/leases/{lease['id']}/periods/{period['id']}/payments"

    r1 = client.post(base, json={"amount": 10000})
    assert r1.json()["status"] == "pending"
    assert r1.json()["amount_paid"] == 10000
    assert sent_emails == []  # частичная оплата — владельцу не пишем

    r2 = client.post(base, json={"amount": 25000})
    assert r2.json()["status"] == "paid"
    assert r2.json()["amount_paid"] == 35000
    assert any("Оплата подтверждена" in e["subject"] for e in sent_emails)


# --- ФТ-5: подтверждение оплаты по ссылке ---

def test_confirm_flow(client, db, sent_emails, monkeypatch):
    from app.models import RentPeriod
    from app.payment_check import VerifyResult
    from app.routers import confirm as confirm_router

    # Подменяем извлечение текста и LLM-проверку — без сети и реального PDF.
    monkeypatch.setattr(confirm_router, "extract_pdf_text", lambda data: "квитанция")
    verdict = {"value": VerifyResult(True, "Оплата подтверждена.")}
    monkeypatch.setattr(confirm_router, "verify_payment", lambda *a, **k: verdict["value"])

    p = _new_property(client)
    lease = client.post(f"/api/properties/{p['id']}/leases", json=_lease_payload()).json()
    token = db.query(RentPeriod).filter(RentPeriod.lease_id == uuid.UUID(lease["id"])).first().confirmation_token

    info = client.get(f"/api/confirm/{token}")
    assert info.status_code == 200
    assert info.json()["amount_due"] == 35000

    pdf = ("receipt.pdf", b"%PDF-1.4 fake", "application/pdf")

    # Не PDF — отклоняем до проверки.
    not_pdf = client.post(f"/api/confirm/{token}", files={"file": ("x.txt", b"hi", "text/plain")})
    assert not_pdf.status_code == 400

    # LLM забраковал квитанцию → 400 с понятной причиной, период не оплачен.
    verdict["value"] = VerifyResult(False, "сумма меньше ожидаемой")
    bad = client.post(f"/api/confirm/{token}", files={"file": pdf})
    assert bad.status_code == 400
    assert "сумма меньше ожидаемой" in bad.json()["detail"]

    # Корректная квитанция → оплата подтверждена, владелец уведомлён.
    verdict["value"] = VerifyResult(True, "Оплата подтверждена.")
    ok = client.post(f"/api/confirm/{token}", files={"file": pdf})
    assert ok.status_code == 200
    assert any("Оплата подтверждена" in e["subject"] for e in sent_emails)

    again = client.post(f"/api/confirm/{token}", files={"file": pdf})
    assert again.status_code == 400


def test_confirm_bad_token_404(client):
    assert client.get("/api/confirm/nope").status_code == 404


# --- ФТ-6: тестовые ручки писем ---

def test_email_test_endpoints(client, db, sent_emails):
    from app.models import RentPeriod

    p = _new_property(client)
    lease = client.post(f"/api/properties/{p['id']}/leases", json=_lease_payload()).json()
    period_id = db.query(RentPeriod).filter(RentPeriod.lease_id == uuid.UUID(lease["id"])).first().id

    for kind in ("tenant-reminder", "owner-paid", "owner-not-paid"):
        r = client.post(f"/api/email/test/{kind}", json={"period_id": str(period_id)})
        assert r.status_code == 200, r.text
    assert len(sent_emails) == 3
