from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.mail import send_owner_not_paid, send_tenant_payment_reminder
from app.models import Lease, PaymentStatus, Property, PropertyStatus


def _confirm_url(token: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/confirm/{token}"


def run_reminder_3d_job(db: Session) -> int:
    """За 3 дня до rent_end — напоминание арендатору (один раз)."""
    today = date.today()
    target = today + timedelta(days=3)
    sent = 0
    leases = (
        db.query(Lease)
        .join(Property)
        .filter(
            Lease.rent_end == target,
            Lease.payment_status == PaymentStatus.pending.value,
            Lease.reminder_3d_sent_at.is_(None),
        )
        .all()
    )
    for lease in leases:
        prop = lease.property
        send_tenant_payment_reminder(
            tenant_email=lease.tenant_email,
            property_name=prop.name,
            address=prop.address,
            rent_end_iso=lease.rent_end.isoformat(),
            confirm_url=_confirm_url(lease.confirmation_token),
        )
        lease.reminder_3d_sent_at = datetime.utcnow()
        sent += 1
    if sent:
        db.commit()
    return sent


def run_overdue_job(db: Session) -> int:
    """После rent_end без оплаты — письмо владельцу (один раз)."""
    today = date.today()
    sent = 0
    leases = (
        db.query(Lease)
        .join(Property)
        .filter(
            Lease.rent_end < today,
            Lease.payment_status == PaymentStatus.pending.value,
            Lease.overdue_notice_sent_at.is_(None),
        )
        .all()
    )
    for lease in leases:
        prop = lease.property
        send_owner_not_paid(
            owner_email=prop.owner_email,
            property_name=prop.name,
            address=prop.address,
            tenant_name=lease.tenant_name,
            rent_end_iso=lease.rent_end.isoformat(),
        )
        lease.payment_status = PaymentStatus.overdue.value
        prop.status = PropertyStatus.free.value
        lease.overdue_notice_sent_at = datetime.utcnow()
        sent += 1
    if sent:
        db.commit()
    return sent
