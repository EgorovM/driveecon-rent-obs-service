import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.mail import send_demo, send_owner_not_paid, send_owner_paid, send_tenant_payment_reminder
from app.models import Lease
from app.schemas import EmailTestBody, MessageOut

router = APIRouter(prefix="/api/email/test", tags=["email-test"])


@router.post("/tenant-reminder", response_model=MessageOut)
def test_tenant_reminder(body: EmailTestBody, db: Session = Depends(get_db)):
    try:
        if body.lease_id:
            lease = db.query(Lease).filter(Lease.id == body.lease_id).first()
            if not lease:
                raise HTTPException(404, "Аренда не найдена")
            prop = lease.property
            dest = str(body.to_email) if body.to_email else lease.tenant_email
            send_tenant_payment_reminder(
                tenant_email=dest,
                property_name=prop.name,
                address=prop.address,
                rent_end_iso=lease.rent_end.isoformat(),
                confirm_url=f"{settings.frontend_url.rstrip('/')}/confirm/{lease.confirmation_token}",
            )
        else:
            send_demo(
                str(body.to_email),
                "Тест: напоминание арендатору",
                "Это тестовое письмо напоминания (без привязки к аренде).",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ошибка SMTP: {e}") from e
    return MessageOut(detail="Письмо арендатору отправлено")


@router.post("/owner-paid", response_model=MessageOut)
def test_owner_paid(body: EmailTestBody, db: Session = Depends(get_db)):
    try:
        if body.lease_id:
            lease = db.query(Lease).filter(Lease.id == body.lease_id).first()
            if not lease:
                raise HTTPException(404, "Аренда не найдена")
            prop = lease.property
            dest = str(body.to_email) if body.to_email else prop.owner_email
            send_owner_paid(
                owner_email=dest,
                property_name=prop.name,
                address=prop.address,
                tenant_name=lease.tenant_name,
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
        if body.lease_id:
            lease = db.query(Lease).filter(Lease.id == body.lease_id).first()
            if not lease:
                raise HTTPException(404, "Аренда не найдена")
            prop = lease.property
            dest = str(body.to_email) if body.to_email else prop.owner_email
            send_owner_not_paid(
                owner_email=dest,
                property_name=prop.name,
                address=prop.address,
                tenant_name=lease.tenant_name,
                rent_end_iso=lease.rent_end.isoformat(),
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
