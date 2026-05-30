import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.mail import month_label, send_owner_paid
from app.models import PeriodStatus, RentPeriod
from app.schemas import ConfirmBody, ConfirmOut, MessageOut

router = APIRouter(tags=["confirm"])


def _validate_confirmation_text(text: str) -> bool:
    t = text.lower().strip()
    if len(t) < 5:
        return False
    ok = re.search(r"оплат|платеж|подтверж|внес|перевел|перевёл|оплатил|paid|ok", t)
    return bool(ok)


def _get_period(db: Session, token: str) -> RentPeriod:
    period = db.query(RentPeriod).filter(RentPeriod.confirmation_token == token).first()
    if not period:
        raise HTTPException(404, "Ссылка недействительна")
    return period


@router.get("/api/confirm/{token}", response_model=ConfirmOut)
def get_confirm_info(token: str, db: Session = Depends(get_db)):
    period = _get_period(db, token)
    lease = period.lease
    prop = lease.property
    return ConfirmOut(
        period_id=period.id,
        property_name=prop.name,
        address=prop.address,
        tenant_name=lease.tenant_name,
        year=period.year,
        month=period.month,
        due_date=period.due_date,
        amount_due=period.amount_due,
        amount_paid=period.amount_paid,
        status=PeriodStatus(period.status),
    )


@router.post("/api/confirm/{token}", response_model=MessageOut)
def post_confirm(token: str, body: ConfirmBody, db: Session = Depends(get_db)):
    period = _get_period(db, token)
    if period.status == PeriodStatus.paid.value:
        raise HTTPException(400, "Оплата за этот период уже подтверждена")

    if not _validate_confirmation_text(body.confirmation_text):
        raise HTTPException(
            400,
            "В тексте подтверждения укажите явно, что оплата произведена (например: «оплатил аренду»).",
        )

    lease = period.lease
    prop = lease.property
    period.amount_paid = period.amount_due
    period.status = PeriodStatus.paid.value
    period.paid_at = datetime.utcnow()
    db.commit()

    send_owner_paid(
        owner_email=prop.owner_email,
        property_name=prop.name,
        address=prop.address,
        tenant_name=lease.tenant_name,
        period_label=month_label(period.year, period.month),
        amount=period.amount_due,
    )

    return MessageOut(ok=True, detail="Владелец уведомлён об оплате.")
