import secrets
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Lease, PaymentStatus, Property, PropertyStatus
from app.parse_lease_txt import parse_lease_txt
from app.schemas import LeaseCreate, LeaseOut, LeaseUpdate

router = APIRouter(prefix="/api/properties", tags=["leases"])


def _create_lease_for_property(db: Session, prop: Property, data: LeaseCreate) -> Lease:
    if data.rent_end < data.rent_start:
        raise HTTPException(400, "Дата окончания раньше даты начала")

    token = secrets.token_urlsafe(32)
    lease = Lease(
        property_id=prop.id,
        tenant_name=data.tenant_name,
        tenant_email=str(data.tenant_email),
        rent_start=data.rent_start,
        rent_end=data.rent_end,
        payment_status=PaymentStatus.pending.value,
        confirmation_token=token,
    )
    prop.status = PropertyStatus.occupied.value
    db.add(lease)
    db.commit()
    db.refresh(lease)
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
    data = LeaseCreate(**parsed)
    return _create_lease_for_property(db, prop, data)


@router.get("/{property_id}/leases", response_model=list[LeaseOut])
def list_leases(property_id: uuid.UUID, db: Session = Depends(get_db)):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(404, "Объект не найден")
    return db.query(Lease).filter(Lease.property_id == property_id).order_by(Lease.created_at.desc()).all()


@router.patch("/{property_id}/leases/{lease_id}", response_model=LeaseOut)
def update_lease(
    property_id: uuid.UUID,
    lease_id: uuid.UUID,
    data: LeaseUpdate,
    db: Session = Depends(get_db),
):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(404, "Объект не найден")
    lease = db.query(Lease).filter(Lease.id == lease_id, Lease.property_id == property_id).first()
    if not lease:
        raise HTTPException(404, "Аренда не найдена")
    if data.tenant_name is not None:
        lease.tenant_name = data.tenant_name
    if data.tenant_email is not None:
        lease.tenant_email = str(data.tenant_email)
    db.commit()
    db.refresh(lease)
    return lease
