import base64
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from license_client import (
    LicenseError,
    LicenseManager,
    canonical_license_bytes,
    device_identifier,
    verify_license_signature,
)


def test_ed25519_license_signature_round_trip():
    key = Ed25519PrivateKey.generate()
    public_key = key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    payload = {
        "license_id": "license-test",
        "email": "buyer@example.com",
        "device_id": "win-test-device",
        "issued_at": datetime(2026, 11, 17, tzinfo=timezone.utc).isoformat(),
        "expires_at": None,
        "offline_grace_days": 14,
        "recheck_days": 7,
    }
    signature = base64.b64encode(key.sign(canonical_license_bytes(payload))).decode("ascii")
    public_b64 = base64.b64encode(public_key).decode("ascii")

    verify_license_signature(payload, signature, public_b64)


def test_invalid_signature_is_rejected():
    key = Ed25519PrivateKey.generate()
    public_key = key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    payload = {"license_id": "license-test", "expires_at": None}
    signature = base64.b64encode(b"x" * 64).decode("ascii")
    public_b64 = base64.b64encode(public_key).decode("ascii")

    with pytest.raises(LicenseError):
        verify_license_signature(payload, signature, public_b64)


def test_missing_pinned_public_key_fails_closed():
    with pytest.raises(LicenseError):
        verify_license_signature({"license_id": "x"}, "signature", "")


def test_device_identifier_has_stable_format():
    first = device_identifier()
    second = device_identifier()
    assert first == second
    assert first.startswith("win-")
    assert len(first) == 60


def test_manager_requires_https_server():
    manager = LicenseManager(api_base_url="http://example.com", public_key_b64="test")
    assert manager.configured() is False
