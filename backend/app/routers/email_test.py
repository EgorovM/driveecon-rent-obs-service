from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.mail import (
    month_label,
    send_demo,
    send_owner_not_paid,
    send_owner_paid,
    send_tenant_payment_reminder,
)
from app.models import RentPeriod
from app.schemas import EmailTestBody, MessageOut

router = APIRouter(prefix="/api/email/test", tags=["email-test"])


def _period_or_404(db: Session, period_id) -> RentPeriod:
    period = db.query(RentPeriod).filter(RentPeriod.id == period_id).first()
    if not period:
        raise HTTPException(404, "Начисление не найдено")
    return period


@router.post("/tenant-reminder", response_model=MessageOut)
def test_tenant_reminder(body: EmailTestBody, db: Session = Depends(get_db)):
    try:
        if body.period_id:
            period = _period_or_404(db, body.period_id)
            lease = period.lease
            prop = lease.property
            dest = str(body.to_email) if body.to_email else lease.tenant_email
            send_tenant_payment_reminder(
                tenant_email=dest,
                property_name=prop.name,
                address=prop.address,
                period_label=month_label(period.year, period.month),
                amount_due=period.amount_due,
                due_date_iso=period.due_date.isoformat(),
                confirm_url=f"{settings.frontend_url.rstrip('/')}/confirm/{period.confirmation_token}",
            )
        else:
            send_demo(
                str(body.to_email),
                "Тест: напоминание арендатору",
                "Это тестовое письмо напоминания (без привязки к начислению).",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ошибка SMTP: {e}") from e
    return MessageOut(detail="Письмо арендатору отправлено")


@router.post("/owner-paid", response_model=MessageOut)
def test_owner_paid(body: EmailTestBody, db: Session = Depends(get_db)):
    try:
        if body.period_id:
            period = _period_or_404(db, body.period_id)
            lease = period.lease
            prop = lease.property
            dest = str(body.to_email) if body.to_email else prop.owner_email
            send_owner_paid(
                owner_email=dest,
                property_name=prop.name,
                address=prop.address,
                tenant_name=lease.tenant_name,
                period_label=month_label(period.year, period.month),
                amount=period.amount_due,
            )
        else:
            send_demo(
                str(body.to_email),
                "Тест: оплата получена",
                "Это тестовое письмо владельцу об оплате.",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ошибка SMTP: {e}") from e
    return MessageOut(detail="Письмо владельцу (оплачено) отправлено")


@router.post("/owner-not-paid", response_model=MessageOut)
def test_owner_not_paid(body: EmailTestBody, db: Session = Depends(get_db)):
    try:
        if body.period_id:
            period = _period_or_404(db, body.period_id)
            lease = period.lease
            prop = lease.property
            dest = str(body.to_email) if body.to_email else prop.owner_email
            send_owner_not_paid(
                owner_email=dest,
                property_name=prop.name,
                address=prop.address,
                tenant_name=lease.tenant_name,
                period_label=month_label(period.year, period.month),
                amount_due=period.amount_due - period.amount_paid,
                due_date_iso=period.due_date.isoformat(),
            )
        else:
            send_demo(
                str(body.to_email),
                "Тест: нет оплаты",
                "Это тестовое письмо владельцу о неоплате.",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ошибка SMTP: {e}") from e
    return MessageOut(detail="Письмо владельцу (не оплатили) отправлено")
