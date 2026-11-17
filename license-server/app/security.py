import base64, hashlib, json, os, secrets
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

def hash_serial(serial: str) -> str:
    return hashlib.sha256(serial.strip().upper().encode()).hexdigest()

def new_serial() -> str:
    return 'WRK-' + '-'.join(secrets.token_hex(2).upper() for _ in range(4))

def private_key():
    raw = os.environ.get('LICENSE_PRIVATE_KEY', '').strip()
    if not raw:
        raise RuntimeError('LICENSE_PRIVATE_KEY is not configured')
    return Ed25519PrivateKey.from_private_bytes(base64.b64decode(raw))

def public_key_b64() -> str:
    raw = private_key().public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(raw).decode('ascii')

def signed_license(license_id, email, device_id, plan, expires_at):
    now = datetime.now(timezone.utc)
    payload = {'iss': os.getenv('LICENSE_ISSUER', 'WARAKA'), 'license_id': license_id, 'email': email, 'device_id': device_id, 'plan': plan, 'iat': int(now.timestamp()), 'exp': int((expires_at or now + timedelta(days=3650)).timestamp())}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(',', ':'), sort_keys=True).encode()).rstrip(b'=')
    signature = private_key().sign(body)
    return body.decode() + '.' + base64.urlsafe_b64encode(signature).rstrip(b'=').decode()
