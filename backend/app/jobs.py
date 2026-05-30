from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.mail import month_label, send_owner_not_paid, send_tenant_payment_reminder
from app.models import Lease, PeriodStatus, Property, RentPeriod
from app.periods import ensure_periods_for_lease


def _confirm_url(token: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/confirm/{token}"


def generate_due_periods(db: Session, today: date | None = None) -> int:
    """Создаёт недостающие месячные начисления по всем арендам. Возвращает число созданных."""
    today = today or date.today()
    created = 0
    for lease in db.query(Lease).all():
        created += ensure_periods_for_lease(db, lease, today=today)
    if created:
        db.commit()
    return created


def run_reminder_3d_job(db: Session, today: date | None = None) -> int:
    """За 3 дня до due_date — напоминание арендатору (один раз на период)."""
    today = today or date.today()
    target = today + timedelta(days=3)
    sent = 0
    periods = (
        db.query(RentPeriod)
        .join(Lease)
        .join(Property)
        .filter(
            RentPeriod.due_date == target,
            RentPeriod.status == PeriodStatus.pending.value,
            RentPeriod.reminder_3d_sent_at.is_(None),
        )
        .all()
    )
    for period in periods:
        lease = period.lease
        prop = lease.property
        send_tenant_payment_reminder(
            tenant_email=lease.tenant_email,
            property_name=prop.name,
            address=prop.address,
            period_label=month_label(period.year, period.month),
            amount_due=period.amount_due,
            due_date_iso=period.due_date.isoformat(),
            confirm_url=_confirm_url(period.confirmation_token),
        )
        period.reminder_3d_sent_at = datetime.utcnow()
        sent += 1
    if sent:
        db.commit()
    return sent


def run_overdue_job(db: Session, today: date | None = None) -> int:
    """После due_date без полной оплаты — письмо владельцу (один раз на период)."""
    today = today or date.today()
    sent = 0
    periods = (
        db.query(RentPeriod)
        .join(Lease)
        .join(Property)
        .filter(
            RentPeriod.due_date < today,
            RentPeriod.status == PeriodStatus.pending.value,
            RentPeriod.overdue_notice_sent_at.is_(None),
        )
        .all()
    )
    for period in periods:
        lease = period.lease
        prop = lease.property
        send_owner_not_paid(
            owner_email=prop.owner_email,
            property_name=prop.name,
            address=prop.address,
            tenant_name=lease.tenant_name,
            period_label=month_label(period.year, period.month),
            amount_due=period.amount_due - period.amount_paid,
            due_date_iso=period.due_date.isoformat(),
        )
        period.status = PeriodStatus.overdue.value
        period.overdue_notice_sent_at = datetime.utcnow()
        sent += 1
    if sent:
        db.commit()
    return sent
