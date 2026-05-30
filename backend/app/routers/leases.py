import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.mail import month_label, send_owner_paid
from app.models import Lease, PeriodStatus, Property, PropertyStatus, RentPeriod
from app.parse_lease_txt import parse_lease_txt
from app.periods import ensure_periods_for_lease, recompute_status
from app.schemas import LeaseCreate, LeaseOut, LeaseUpdate, PaymentCreate, RentPeriodOut

router = APIRouter(prefix="/api/properties", tags=["leases"])


def _create_lease_for_property(db: Session, prop: Property, data: LeaseCreate) -> Lease:
    lease = Lease(
        property_id=prop.id,
        tenant_name=data.tenant_name,
        tenant_email=str(data.tenant_email),
        rent_start=data.rent_start,
        rent_end=data.rent_end,
        rent_amount=data.rent_amount,
        payment_day=data.payment_day,
        contract_number=data.contract_number,
        contract_date=data.contract_date,
    )
    prop.status = PropertyStatus.occupied.value
    db.add(lease)
    db.flush()
    ensure_periods_for_lease(db, lease)
    db.commit()
    db.refresh(lease)
    return lease


def _get_lease(db: Session, property_id: uuid.UUID, lease_id: uuid.UUID) -> Lease:
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(404, "Объект не найден")
    lease = db.query(Lease).filter(Lease.id == lease_id, Lease.property_id == property_id).first()
    if not lease:
        raise HTTPException(404, "Аренда не найдена")
    return lease


@router.post("/{property_id}/leases", response_model=LeaseOut)
def create_lease_manual(property_id: uuid.UUID, data: LeaseCreate, db: Session = Depends(get_db)):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(404, "Объект не найден")
    return _create_lease_for_property(db, prop, data)


@router.post("/{property_id}/leases/upload", response_model=LeaseOut)
async def create_lease_upload(
    property_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(404, "Объект не найден")
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp1251", errors="replace")
    try:
        parsed = parse_lease_txt(text)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    try:
        data = LeaseCreate(**parsed)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _create_lease_for_property(db, prop, data)


@router.get("/{property_id}/leases", response_model=list[LeaseOut])
def list_leases(property_id: uuid.UUID, db: Session = Depends(get_db)):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(404, "Объект не найден")
    return (
        db.query(Lease)
        .filter(Lease.property_id == property_id)
        .order_by(Lease.created_at.desc())
        .all()
    )


@router.patch("/{property_id}/leases/{lease_id}", response_model=LeaseOut)
def update_lease(
    property_id: uuid.UUID,
    lease_id: uuid.UUID,
    data: LeaseUpdate,
    db: Session = Depends(get_db),
):
    lease = _get_lease(db, property_id, lease_id)
    if data.tenant_name is not None:
        lease.tenant_name = data.tenant_name
    if data.tenant_email is not None:
        lease.tenant_email = str(data.tenant_email)
    if data.rent_amount is not None:
        lease.rent_amount = data.rent_amount
    if data.payment_day is not None:
        lease.payment_day = data.payment_day
    if data.terminated_at is not None:
        lease.terminated_at = data.terminated_at
        if lease.property.status == PropertyStatus.occupied.value:
            lease.property.status = PropertyStatus.free.value
    db.commit()
    db.refresh(lease)
    return lease


@router.get("/{property_id}/leases/{lease_id}/periods", response_model=list[RentPeriodOut])
def list_periods(property_id: uuid.UUID, lease_id: uuid.UUID, db: Session = Depends(get_db)):
    lease = _get_lease(db, property_id, lease_id)
    return (
        db.query(RentPeriod)
        .filter(RentPeriod.lease_id == lease.id)
        .order_by(RentPeriod.due_date)
        .all()
    )


@router.post("/{property_id}/leases/{lease_id}/periods/{period_id}/payments", response_model=RentPeriodOut)
def record_payment(
    property_id: uuid.UUID,
    lease_id: uuid.UUID,
    period_id: uuid.UUID,
    data: PaymentCreate,
    db: Session = Depends(get_db),
):
    """Зафиксировать фактическое поступление (поддерживает частичные оплаты/долги).

    Когда сумма оплат достигает начисления, период становится «оплачено» и владелец уведомляется.
    """
    lease = _get_lease(db, property_id, lease_id)
    period = (
        db.query(RentPeriod)
        .filter(RentPeriod.id == period_id, RentPeriod.lease_id == lease.id)
        .first()
    )
    if not period:
        raise HTTPException(404, "Начисление не найдено")

    was_paid = period.status == PeriodStatus.paid.value
    period.amount_paid += data.amount
    recompute_status(period)
    if period.status == PeriodStatus.paid.value and not was_paid:
        period.paid_at = datetime.utcnow()
    db.commit()
    db.refresh(period)

    if period.status == PeriodStatus.paid.value and not was_paid:
        prop = lease.property
        send_owner_paid(
            owner_email=prop.owner_email,
            property_name=prop.name,
            address=prop.address,
            tenant_name=lease.tenant_name,
            period_label=month_label(period.year, period.month),
            amount=period.amount_due,
        )
    return period
