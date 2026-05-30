from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.mail import month_label, send_owner_paid
from app.models import PeriodStatus, RentPeriod
from app.payment_check import PdfExtractError, extract_pdf_text, verify_payment
from app.schemas import ConfirmOut, MessageOut

router = APIRouter(tags=["confirm"])

MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 МБ


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
async def post_confirm(
    token: str,
    file: UploadFile = File(..., description="PDF-квитанция об оплате из банка"),
    db: Session = Depends(get_db),
):
    period = _get_period(db, token)
    if period.status == PeriodStatus.paid.value:
        raise HTTPException(400, "Оплата за этот период уже подтверждена")

    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()
    if not (filename.endswith(".pdf") or "pdf" in content_type):
        raise HTTPException(400, "Прикрепите файл в формате PDF (квитанция из банка).")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Файл пустой. Прикрепите PDF-квитанцию об оплате.")
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(400, "Файл слишком большой (максимум 10 МБ).")

    try:
        pdf_text = extract_pdf_text(data)
    except PdfExtractError as e:
        raise HTTPException(400, str(e)) from e

    lease = period.lease
    prop = lease.property
    period_label = month_label(period.year, period.month)

    try:
        result = verify_payment(
            pdf_text,
            amount_due=period.amount_due,
            period_label=period_label,
            property_name=prop.name,
            tenant_name=lease.tenant_name,
        )
    except RuntimeError as e:
        raise HTTPException(502, f"Не удалось проверить квитанцию: {e}") from e

    if not result.ok:
        raise HTTPException(400, f"Квитанция не подтверждает оплату: {result.reason}")

    period.amount_paid = period.amount_due
    period.status = PeriodStatus.paid.value
    period.paid_at = datetime.utcnow()
    db.commit()

    send_owner_paid(
        owner_email=prop.owner_email,
        property_name=prop.name,
        address=prop.address,
        tenant_name=lease.tenant_name,
        period_label=period_label,
        amount=period.amount_due,
    )

    detail = "Квитанция проверена, оплата подтверждена. Владелец уведомлён."
    if result.reason:
        detail = f"{result.reason} Владелец уведомлён об оплате."
    return MessageOut(ok=True, detail=detail)
