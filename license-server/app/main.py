import os
import hmac
import hashlib
import secrets
import smtplib
from email.message import EmailMessage
from datetime import datetime, timezone, timedelta
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from .database import Base, engine, get_db
from .models import ActivationCode, Device, License
from .security import hash_serial, new_serial, public_key_b64, signed_license

app = FastAPI(title='WARAKA License API', version='0.2.0', docs_url='/docs')
Base.metadata.create_all(bind=engine)

class ActivationCodeRequest(BaseModel):
    serial: str = Field(min_length=8, max_length=64)
    email: EmailStr

class ActivateRequest(ActivationCodeRequest):
    code: str = Field(min_length=6, max_length=6, pattern='^[0-9]{6}$')
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
    if not expected or not x_admin_key or not hmac.compare_digest(x_admin_key, expected):
        raise HTTPException(status_code=401, detail='Unauthorized')

def code_digest(code: str) -> str:
    pepper = os.getenv('OTP_SECRET', '')
    if len(pepper) < 32:
        raise HTTPException(status_code=503, detail='Email verification is not configured')
    return hmac.new(pepper.encode(), code.encode(), hashlib.sha256).hexdigest()

def send_activation_email(recipient: str, code: str):
    required = ['SMTP_HOST', 'SMTP_USER', 'SMTP_PASSWORD', 'SMTP_FROM']
    if any(not os.getenv(k) for k in required):
        raise RuntimeError('SMTP settings are incomplete')
    host = os.environ['SMTP_HOST']
    port = int(os.getenv('SMTP_PORT', '587'))
    msg = EmailMessage()
    msg['Subject'] = 'رمز تفعيل WARAKA'
    msg['From'] = os.environ['SMTP_FROM']
    msg['To'] = recipient
    msg.set_content(f'رمز التحقق الخاص بتفعيل WARAKA هو: {code}\n\nتنتهي صلاحية الرمز خلال 10 دقائق. لا تشارك هذا الرمز مع أي شخص.')
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
        smtp.send_message(msg)

@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'WARAKA License API'}

@app.get('/v1/public-key')
def get_public_key():
    try:
        return {'algorithm': 'Ed25519', 'public_key': public_key_b64()}
    except Exception:
        raise HTTPException(status_code=503, detail='Signing key is not configured')

@app.post('/v1/activation/request-code')
def request_activation_code(data: ActivationCodeRequest, db: Session = Depends(get_db)):
    email = str(data.email).lower()
    lic = db.scalar(select(License).where(License.serial_hash == hash_serial(data.serial), License.email == email, License.active.is_(True)))
    if not lic:
        raise HTTPException(status_code=403, detail='License credentials are invalid or inactive')
    now = datetime.now(timezone.utc)
    latest = db.scalar(select(ActivationCode).where(ActivationCode.license_id == lic.id).order_by(ActivationCode.created_at.desc()).limit(1))
    if latest and latest.created_at > now - timedelta(seconds=60):
        raise HTTPException(status_code=429, detail='Please wait before requesting another code')
    code = f'{secrets.randbelow(1_000_000):06d}'
    record = ActivationCode(license_id=lic.id, code_hash=code_digest(code), expires_at=now + timedelta(minutes=10))
    db.add(record)
    db.commit()
    try:
        send_activation_email(email, code)
    except Exception:
        record.consumed = True
        db.commit()
        raise HTTPException(status_code=503, detail='Unable to send verification email; check server SMTP settings')
    return {'status': 'code_sent', 'expires_in_seconds': 600}

@app.post('/v1/activate')
def activate(data: ActivateRequest, db: Session = Depends(get_db)):
    email = str(data.email).lower()
    lic = db.scalar(select(License).options(selectinload(License.devices)).where(License.serial_hash == hash_serial(data.serial), License.email == email, License.active.is_(True)))
    if not lic:
        raise HTTPException(status_code=403, detail='License credentials are invalid or inactive')
    now = datetime.now(timezone.utc)
    if lic.expires_at and lic.expires_at <= now:
        raise HTTPException(status_code=403, detail='License expired')
    verification = db.scalar(select(ActivationCode).where(ActivationCode.license_id == lic.id, ActivationCode.consumed.is_(False)).order_by(ActivationCode.created_at.desc()).limit(1))
    if not verification or verification.expires_at <= now or verification.attempts >= 5:
        raise HTTPException(status_code=403, detail='Verification code is missing, expired, or locked')
    if not hmac.compare_digest(verification.code_hash, code_digest(data.code)):
        verification.attempts += 1
        db.commit()
        raise HTTPException(status_code=403, detail='Invalid verification code')
    device = next((d for d in lic.devices if d.device_id == data.device_id and d.active), None)
    if device is None:
        if sum(1 for d in lic.devices if d.active) >= 3:
            raise HTTPException(status_code=409, detail='Device limit reached (3)')
        device = db.scalar(select(Device).where(Device.license_id == lic.id, Device.device_id == data.device_id))
        if device:
            device.active = True
            device.device_name = data.device_name
        else:
            device = Device(license_id=lic.id, device_id=data.device_id, device_name=data.device_name)
            db.add(device)
    device.last_seen_at = now
    verification.consumed = True
    db.commit()
    token = signed_license(lic.id, lic.email, data.device_id, lic.plan, lic.expires_at)
    return {'status': 'activated', 'license_token': token, 'license_id': lic.id, 'plan': lic.plan, 'device_limit': 3}

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

@app.post('/v1/deactivate', dependencies=[Depends(require_admin)])
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
    return [{'id': l.id, 'email': l.email, 'plan': l.plan, 'active': l.active, 'expires_at': l.expires_at, 'devices': [{'device_id': d.device_id, 'device_name': d.device_name, 'active': d.active, 'last_seen_at': d.last_seen_at} for d in l.devices]} for l in rows]

@app.post('/v1/admin/licenses/{license_id}/disable', dependencies=[Depends(require_admin)])
def disable_license(license_id: int, db: Session = Depends(get_db)):
    lic = db.get(License, license_id)
    if not lic:
        raise HTTPException(status_code=404, detail='License not found')
    lic.active = False
    db.commit()
    return {'status': 'disabled', 'license_id': lic.id}
