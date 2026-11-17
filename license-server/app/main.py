import os
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from .database import Base, engine, get_db
from .models import Device, License
from .security import hash_serial, new_serial, public_key_b64, signed_license

app = FastAPI(title='WARAKA License API', version='0.1.0', docs_url='/docs')
Base.metadata.create_all(bind=engine)

class ActivateRequest(BaseModel):
    serial: str = Field(min_length=8, max_length=64)
    email: EmailStr
    device_id: str = Field(min_length=8, max_length=128)
    device_name: str = Field(default='Windows PC', max_length=128)

class ValidateRequest(BaseModel):
    license_id: int
    device_id: str = Field(min_length=8, max_length=128)

class CreateLicenseRequest(BaseModel):
    email: EmailStr
    plan: str = Field(default='pro', pattern='^(pro|reader)$')
    expires_at: datetime | None = None

class DeviceRequest(BaseModel):
    license_id: int
    device_id: str

def require_admin(x_admin_key: str | None = Header(default=None)):
    expected = os.getenv('ADMIN_API_KEY', '')
    if not expected or not x_admin_key or not __import__('hmac').compare_digest(x_admin_key, expected):
        raise HTTPException(status_code=401, detail='Unauthorized')

@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'WARAKA License API'}

@app.get('/v1/public-key')
def get_public_key():
    try:
        return {'algorithm': 'Ed25519', 'public_key': public_key_b64()}
    except Exception:
        raise HTTPException(status_code=503, detail='Signing key is not configured')

@app.post('/v1/activate')
def activate(data: ActivateRequest, db: Session = Depends(get_db)):
    license_obj = db.scalar(select(License).options(selectinload(License.devices)).where(License.serial_hash == hash_serial(data.serial)))
    if not license_obj or not license_obj.active or license_obj.email.lower() != str(data.email).lower():
        raise HTTPException(status_code=403, detail='License credentials are invalid or inactive')
    now = datetime.now(timezone.utc)
    if license_obj.expires_at and license_obj.expires_at <= now:
        raise HTTPException(status_code=403, detail='License expired')
    device = next((d for d in license_obj.devices if d.device_id == data.device_id and d.active), None)
    if device is None:
        if sum(1 for d in license_obj.devices if d.active) >= 3:
            raise HTTPException(status_code=409, detail='Device limit reached (3)')
        device = Device(license_id=license_obj.id, device_id=data.device_id, device_name=data.device_name)
        db.add(device)
    device.last_seen_at = now
    db.commit()
    token = signed_license(license_obj.id, license_obj.email, data.device_id, license_obj.plan, license_obj.expires_at)
    return {'status': 'activated', 'license_token': token, 'license_id': license_obj.id, 'plan': license_obj.plan, 'device_limit': 3}

@app.post('/v1/validate')
def validate(data: ValidateRequest, db: Session = Depends(get_db)):
    lic = db.get(License, data.license_id)
    if not lic or not lic.active or (lic.expires_at and lic.expires_at <= datetime.now(timezone.utc)):
        raise HTTPException(status_code=403, detail='License inactive or expired')
    device = db.scalar(select(Device).where(Device.license_id == lic.id, Device.device_id == data.device_id, Device.active.is_(True)))
    if not device:
        raise HTTPException(status_code=403, detail='Device is not activated')
    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    return {'status': 'valid', 'plan': lic.plan, 'checked_at': device.last_seen_at.isoformat()}

@app.post('/v1/deactivate')
def deactivate(data: DeviceRequest, db: Session = Depends(get_db)):
    device = db.scalar(select(Device).where(Device.license_id == data.license_id, Device.device_id == data.device_id, Device.active.is_(True)))
    if not device:
        raise HTTPException(status_code=404, detail='Active device not found')
    device.active = False
    db.commit()
    return {'status': 'deactivated'}

@app.post('/v1/admin/licenses', dependencies=[Depends(require_admin)])
def create_license(data: CreateLicenseRequest, db: Session = Depends(get_db)):
    email = str(data.email).lower()
    if db.scalar(select(License).where(License.email == email)):
        raise HTTPException(status_code=409, detail='A license already exists for this email')
    serial = new_serial()
    obj = License(serial_hash=hash_serial(serial), email=email, plan=data.plan, expires_at=data.expires_at)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {'id': obj.id, 'serial': serial, 'email': obj.email, 'plan': obj.plan, 'expires_at': obj.expires_at}

@app.get('/v1/admin/licenses', dependencies=[Depends(require_admin)])
def list_licenses(db: Session = Depends(get_db)):
    rows = db.scalars(select(License).options(selectinload(License.devices)).order_by(License.created_at.desc())).all()
    return [{'id': l.id, 'email': l.email, 'plan': l.plan, 'active': l.active, 'devices': [{'device_id': d.device_id, 'device_name': d.device_name, 'active': d.active} for d in l.devices]} for l in rows]

@app.post('/v1/admin/licenses/{license_id}/disable', dependencies=[Depends(require_admin)])
def disable_license(license_id: int, db: Session = Depends(get_db)):
    lic = db.get(License, license_id)
    if not lic:
        raise HTTPException(status_code=404, detail='License not found')
    lic.active = False
    db.commit()
    return {'status': 'disabled', 'license_id': lic.id}
