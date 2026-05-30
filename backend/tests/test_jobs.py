"""ФТ: планировщик — генерация начислений, напоминание за 3 дня, просрочка."""

import secrets
from datetime import date, timedelta

from app.jobs import generate_due_periods, run_overdue_job, run_reminder_3d_job
from app.models import Lease, PeriodStatus, Property, PropertyStatus, RentPeriod
from app.periods import due_date_for, ensure_periods_for_lease


def _make_lease(db, *, rent_start, rent_end, payment_day=17, rent_amount=35000):
    prop = Property(
        name="Объект", address="Адрес", status=PropertyStatus.occupied.value, owner_email="owner@example.com"
    )
    db.add(prop)
    db.flush()
    lease = Lease(
        property_id=prop.id,
        tenant_name="ИП Тест",
        tenant_email="tenant@mail.ru",
        rent_start=rent_start,
        rent_end=rent_end,
        rent_amount=rent_amount,
        payment_day=payment_day,
    )
    db.add(lease)
    db.flush()
    return lease


def _add_period(db, lease, *, year, month, due_date, amount_due=35000, amount_paid=0, status=PeriodStatus.pending):
    period = RentPeriod(
        lease_id=lease.id,
        year=year,
        month=month,
        due_date=due_date,
        amount_due=amount_due,
        amount_paid=amount_paid,
        status=status.value,
        confirmation_token=secrets.token_urlsafe(16),
    )
    db.add(period)
    db.flush()
    return period


def test_due_date_for_clamps_short_month():
    assert due_date_for(2026, 2, 31) == date(2026, 2, 28)
    assert due_date_for(2024, 2, 31) == date(2024, 2, 29)  # високосный
    assert due_date_for(2026, 1, 17) == date(2026, 1, 17)


def test_ensure_periods_idempotent(db):
    lease = _make_lease(db, rent_start=date(2026, 1, 1), rent_end=date(2026, 12, 31))
    today = date(2026, 3, 10)
    n1 = ensure_periods_for_lease(db, lease, today=today)
    db.commit()
    assert n1 >= 1
    db.refresh(lease)
    n2 = ensure_periods_for_lease(db, lease, today=today)
    assert n2 == 0  # повторный прогон ничего не создаёт


def test_ensure_periods_stops_after_termination(db):
    lease = _make_lease(db, rent_start=date(2026, 1, 1), rent_end=date(2026, 12, 31))
    lease.terminated_at = date(2026, 2, 15)
    db.flush()
    ensure_periods_for_lease(db, lease, today=date(2026, 6, 1))
    db.commit()
    db.refresh(lease)
    months = {(p.year, p.month) for p in lease.periods}
    assert months == {(2026, 1), (2026, 2)}


def test_reminder_3d_job_sends_once(db, sent_emails):
    today = date(2026, 3, 1)
    lease = _make_lease(db, rent_start=date(2026, 3, 1), rent_end=date(2026, 12, 31))
    _add_period(db, lease, year=2026, month=3, due_date=today + timedelta(days=3))
    db.commit()

    sent = run_reminder_3d_job(db, today=today)
    assert sent == 1
    assert len(sent_emails) == 1
    assert "Напоминание об оплате" in sent_emails[0]["subject"]
    assert "35 000 ₽" in sent_emails[0]["body"]

    # Идемпотентность: повторный прогон в тот же день не дублирует.
    assert run_reminder_3d_job(db, today=today) == 0


def test_reminder_skips_far_periods(db, sent_emails):
    today = date(2026, 3, 1)
    lease = _make_lease(db, rent_start=date(2026, 3, 1), rent_end=date(2026, 12, 31))
    _add_period(db, lease, year=2026, month=3, due_date=today + timedelta(days=10))
    db.commit()
    assert run_reminder_3d_job(db, today=today) == 0


def test_overdue_job_notifies_owner_and_marks(db, sent_emails):
    today = date(2026, 4, 1)
    lease = _make_lease(db, rent_start=date(2026, 1, 1), rent_end=date(2026, 12, 31))
    period = _add_period(db, lease, year=2026, month=3, due_date=date(2026, 3, 17))
    db.commit()

    sent = run_overdue_job(db, today=today)
    assert sent == 1
    db.refresh(period)
    assert period.status == PeriodStatus.overdue.value
    assert "Нет оплаты" in sent_emails[0]["subject"]
    assert sent_emails[0]["to"] == "owner@example.com"

    assert run_overdue_job(db, today=today) == 0


def test_overdue_skips_paid(db, sent_emails):
    today = date(2026, 4, 1)
    lease = _make_lease(db, rent_start=date(2026, 1, 1), rent_end=date(2026, 12, 31))
    _add_period(
        db, lease, year=2026, month=3, due_date=date(2026, 3, 17),
        amount_paid=35000, status=PeriodStatus.paid,
    )
    db.commit()
    assert run_overdue_job(db, today=today) == 0
    assert sent_emails == []


def test_generate_due_periods_all_leases(db):
    _make_lease(db, rent_start=date(2026, 1, 1), rent_end=date(2026, 12, 31))
    _make_lease(db, rent_start=date(2026, 1, 1), rent_end=date(2026, 12, 31), payment_day=5)
    db.commit()
    created = generate_due_periods(db, today=date(2026, 2, 1))
    assert created >= 4  # по 2+ периода на каждую аренду
