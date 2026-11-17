import base64
import os
import unittest
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from license_client import (
    LicenseError,
    LicenseManager,
    canonical_license_bytes,
    device_identifier,
    verify_license_signature,
    _dpapi_transform,
)


class LicenseClientTests(unittest.TestCase):
    def test_ed25519_license_signature_round_trip(self):
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

    def test_invalid_signature_is_rejected(self):
        key = Ed25519PrivateKey.generate()
        public_key = key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        payload = {"license_id": "license-test", "expires_at": None}
        signature = base64.b64encode(b"x" * 64).decode("ascii")
        public_b64 = base64.b64encode(public_key).decode("ascii")

        with self.assertRaises(LicenseError):
            verify_license_signature(payload, signature, public_b64)

    def test_missing_pinned_public_key_fails_closed(self):
        with self.assertRaises(LicenseError):
            verify_license_signature({"license_id": "x"}, "signature", "")

    def test_device_identifier_has_stable_format(self):
        first = device_identifier()
        second = device_identifier()
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("win-"))
        self.assertEqual(len(first), 60)

    def test_manager_requires_https_server(self):
        manager = LicenseManager(api_base_url="http://example.com", public_key_b64="test")
        self.assertFalse(manager.configured())

    def test_create_checkout_uses_fixed_local_payment_methods_and_idempotency(self):
        manager = LicenseManager(api_base_url="https://api.example", public_key_b64="test")
        captured = {}

        def fake_request(path, body, extra_headers=None):
            captured["path"] = path
            captured["body"] = body
            captured["headers"] = extra_headers
            return {
                "payment_id": "payment-1",
                "checkout_url": "https://pay.chargily.dz/test/checkouts/1/pay",
                "amount": 2400,
                "currency": "dzd",
                "status": "pending",
            }

        manager._request = fake_request
        result = manager.create_checkout(
            "buyer@example.com",
            "cib",
            "ar",
            "stable-idempotency-key",
        )

        self.assertEqual(captured["path"], "/v1/payments/chargily/checkout")
        self.assertEqual(captured["body"]["payment_method"], "cib")
        self.assertEqual(captured["body"]["email"], "buyer@example.com")
        self.assertEqual(captured["headers"]["Idempotency-Key"], "stable-idempotency-key")
        self.assertEqual(result["payment_id"], "payment-1")

    def test_create_checkout_rejects_non_chargily_redirect(self):
        manager = LicenseManager(api_base_url="https://api.example", public_key_b64="test")
        manager._request = lambda *args, **kwargs: {
            "payment_id": "payment-2",
            "checkout_url": "https://evil.example/pay",
            "amount": 2400,
            "currency": "dzd",
        }
        with self.assertRaises(LicenseError):
            manager.create_checkout("buyer@example.com", "edahabia")

    def test_offline_use_is_allowed_inside_grace_period(self):
        manager = LicenseManager(api_base_url="https://api.example", public_key_b64="test")
        last_verified = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        record = {
            "serial": "WRK-AAAA-BBBB-CCCC-DDDD",
            "email": "buyer@example.com",
            "license": {"issued_at": last_verified, "expires_at": None, "offline_grace_days": 14, "recheck_days": 7},
            "last_verified_at": last_verified,
        }
        manager.load_record = lambda: record
        manager._request = lambda *args, **kwargs: (_ for _ in ()).throw(LicenseError("offline"))
        self.assertIs(manager.check_status(), record)

    def test_offline_use_is_blocked_after_grace_period(self):
        manager = LicenseManager(api_base_url="https://api.example", public_key_b64="test")
        last_verified = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
        record = {
            "serial": "WRK-AAAA-BBBB-CCCC-DDDD",
            "email": "buyer@example.com",
            "license": {"issued_at": last_verified, "expires_at": None, "offline_grace_days": 14, "recheck_days": 7},
            "last_verified_at": last_verified,
        }
        manager.load_record = lambda: record
        manager._request = lambda *args, **kwargs: (_ for _ in ()).throw(LicenseError("offline"))
        with self.assertRaises(LicenseError):
            manager.check_status()

    @unittest.skipUnless(os.name == "nt", "Windows DPAPI is available only on Windows")
    def test_windows_dpapi_protect_unprotect_round_trip(self):
        original = b"WARAKA local license storage test"
        protected = _dpapi_transform(original, protect=True)
        self.assertNotEqual(protected, original)
        self.assertEqual(_dpapi_transform(protected, protect=False), original)


if __name__ == "__main__":
    unittest.main()
