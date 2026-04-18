import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.mail import send_owner_paid
from app.models import Lease, PaymentStatus, Property
from app.schemas import ConfirmBody, ConfirmOut, MessageOut

router = APIRouter(tags=["confirm"])


def _validate_confirmation_text(text: str) -> bool:
    t = text.lower().strip()
    if len(t) < 5:
        return False
    ok = re.search(r"оплат|платеж|подтверж|внес|перевел|перевёл|оплатил|paid|ok", t)
    return bool(ok)


@router.get("/api/confirm/{token}", response_model=ConfirmOut)
def get_confirm_info(token: str, db: Session = Depends(get_db)):
    lease = db.query(Lease).filter(Lease.confirmation_token == token).first()
    if not lease:
        raise HTTPException(404, "Ссылка недействительна")
    prop = lease.property
    return ConfirmOut(
        lease_id=lease.id,
        property_name=prop.name,
        address=prop.address,
        tenant_name=lease.tenant_name,
        rent_end=lease.rent_end,
    )


@router.post("/api/confirm/{token}", response_model=MessageOut)
def post_confirm(token: str, body: ConfirmBody, db: Session = Depends(get_db)):
    lease = db.query(Lease).filter(Lease.confirmation_token == token).first()
    if not lease:
        raise HTTPException(404, "Ссылка недействительна")
    if lease.payment_status != PaymentStatus.pending.value:
        raise HTTPException(400, "Оплата уже подтверждена или просрочена")

    if not _validate_confirmation_text(body.confirmation_text):
        raise HTTPException(
            400,
            "В тексте подтверждения укажите явно, что оплата произведена (например: «оплатил аренду»).",
        )

    prop = lease.property
    lease.payment_status = PaymentStatus.paid.value
    db.commit()

    send_owner_paid(
        owner_email=prop.owner_email,
        property_name=prop.name,
        address=prop.address,
        tenant_name=lease.tenant_name,
    )

    return MessageOut(ok=True, detail="Владелец уведомлён об оплате.")
