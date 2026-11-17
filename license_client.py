"""WARAKA license client for the Windows PDF Splitter application.

The production API URL and Ed25519 public key are deliberately left unconfigured
until the WARAKA backend has been deployed and its production key is installed.
License records are protected with the current Windows user's DPAPI.
"""
import base64
import ctypes
import hashlib
import json
import os
import platform
import ssl
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

import certifi
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


API_BASE_URL = os.environ.get("WARAKA_API_BASE_URL", "").strip().rstrip("/")
# Pin the production key in this source file after Render has its production key.
LICENSE_PUBLIC_KEY_B64 = ""


class LicenseError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def canonical_license_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def verify_license_signature(payload: dict, signature_b64: str, public_key_b64: str) -> None:
    if not public_key_b64:
        raise LicenseError("The WARAKA public verification key is not installed in this build.")
    try:
        public_bytes = base64.b64decode(public_key_b64, validate=True)
        signature = base64.b64decode(signature_b64, validate=True)
        if len(public_bytes) != 32:
            raise ValueError("Invalid Ed25519 public key length")
        Ed25519PublicKey.from_public_bytes(public_bytes).verify(
            signature,
            canonical_license_bytes(payload),
        )
    except Exception as exc:
        raise LicenseError("The license signature is invalid.") from exc


def device_identifier() -> str:
    machine_guid = ""
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            ) as key:
                machine_guid = str(winreg.QueryValueEx(key, "MachineGuid")[0])
        except OSError:
            machine_guid = ""
    source = machine_guid or f"{platform.node()}|{uuid.getnode()}|{platform.platform()}"
    return "win-" + hashlib.sha256(source.encode("utf-8")).hexdigest()[:56]


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.c_ulong),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def _dpapi_transform(data: bytes, protect: bool) -> bytes:
    if os.name != "nt":
        raise LicenseError("Windows DPAPI is required to protect the local license.")
    crypt32 = ctypes.WinDLL("Crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("Kernel32", use_last_error=True)
    blob_type = ctypes.POINTER(_DataBlob)
    crypt_fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    if protect:
        crypt_fn.argtypes = [
            blob_type, ctypes.c_wchar_p, blob_type, ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_ulong, blob_type,
        ]
    else:
        crypt_fn.argtypes = [
            blob_type, ctypes.POINTER(ctypes.c_wchar_p), blob_type,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, blob_type,
        ]
    crypt_fn.restype = ctypes.c_int

    input_buffer = ctypes.create_string_buffer(data, len(data))
    input_blob = _DataBlob(
        len(data),
        ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_byte)),
    )
    output_blob = _DataBlob()
    description = ctypes.c_wchar_p()
    flags = 0x1  # CRYPTPROTECT_UI_FORBIDDEN
    if protect:
        ok = crypt_fn(
            ctypes.byref(input_blob), "WARAKA license", None,
            None, None, flags, ctypes.byref(output_blob),
        )
    else:
        ok = crypt_fn(
            ctypes.byref(input_blob), ctypes.byref(description), None,
            None, None, flags, ctypes.byref(output_blob),
        )
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        kernel32.LocalFree(ctypes.cast(output_blob.pbData, ctypes.c_void_p))


class LicenseManager:
    def __init__(self, api_base_url: str | None = None, public_key_b64: str | None = None):
        self.api_base_url = (api_base_url if api_base_url is not None else API_BASE_URL).strip().rstrip("/")
        self.public_key_b64 = LICENSE_PUBLIC_KEY_B64 if public_key_b64 is None else public_key_b64
        local_root = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
        self.license_path = local_root / "WARAKA" / "license.dat"
        self.device_id = device_identifier()
        self.device_name = platform.node()[:200] or "Windows PC"

    def configured(self) -> bool:
        parsed = urllib.parse.urlparse(self.api_base_url)
        return parsed.scheme == "https" and bool(parsed.netloc) and bool(self.public_key_b64)

    def _request(self, path: str, body: dict, extra_headers: dict | None = None) -> dict:
        if not self.api_base_url:
            raise LicenseError("The WARAKA licensing server has not been configured.")
        parsed = urllib.parse.urlparse(self.api_base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise LicenseError("The WARAKA API address must use HTTPS.")
        url = self.api_base_url + path
        raw = json.dumps(body, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=raw,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "WARAKA-PDF-Splitter",
                **(extra_headers or {}),
            },
            method="POST",
        )
        context = ssl.create_default_context(cafile=certifi.where())
        try:
            with urllib.request.urlopen(request, timeout=20, context=context) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                error_body = json.loads(exc.read().decode("utf-8"))
                message = error_body.get("detail", "The licensing server rejected the request.")
            except Exception:
                message = "The licensing server rejected the request."
            raise LicenseError(str(message), exc.code) from exc
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise LicenseError("Could not reach the WARAKA licensing server.") from exc
        if not isinstance(result, dict):
            raise LicenseError("The licensing server returned an invalid response.")
        return result

    def create_checkout(
        self,
        email: str,
        payment_method: str = "edahabia",
        locale: str = "ar",
        idempotency_key: str | None = None,
    ) -> dict:
        if payment_method not in {"edahabia", "cib"}:
            raise LicenseError("Choose EDAHABIA or CIB for local payment.")
        if locale not in {"ar", "en", "fr"}:
            locale = "ar"
        result = self._request(
            "/v1/payments/chargily/checkout",
            {
                "email": email.strip(),
                "payment_method": payment_method,
                "locale": locale,
            },
            extra_headers={"Idempotency-Key": idempotency_key or uuid.uuid4().hex},
        )
        checkout_url = result.get("checkout_url")
        host = urllib.parse.urlparse(checkout_url).hostname if isinstance(checkout_url, str) else None
        if (
            not isinstance(result.get("payment_id"), str)
            or not isinstance(checkout_url, str)
            or urllib.parse.urlparse(checkout_url).scheme != "https"
            or not host
            or not (host == "chargily.dz" or host.endswith(".chargily.dz")
                    or host == "chargily.net" or host.endswith(".chargily.net"))
            or str(result.get("currency", "")).lower() != "dzd"
            or type(result.get("amount")) is not int
            or result.get("amount", 0) <= 0
        ):
            raise LicenseError("The payment gateway returned an invalid checkout link.")
        return result

    def request_otp(self, serial: str, email: str) -> dict:
        return self._request("/v1/otp/request", {"serial": serial.strip(), "email": email.strip()})

    def activate(self, serial: str, email: str, code: str) -> dict:
        result = self._request(
            "/v1/license/activate",
            {
                "serial": serial.strip(),
                "email": email.strip(),
                "code": code.strip(),
                "device_id": self.device_id,
                "device_name": self.device_name,
            },
        )
        payload = result.get("license")
        signature = result.get("signature")
        if not isinstance(payload, dict) or not isinstance(signature, str):
            raise LicenseError("The licensing server returned an incomplete license.")
        verify_license_signature(payload, signature, self.public_key_b64)
        if payload.get("device_id") != self.device_id:
            raise LicenseError("This license was issued for a different device.")
        self._validate_expiry(payload)
        record = {
            "serial": serial.strip(),
            "email": email.strip(),
            "license": payload,
            "signature": signature,
            "last_verified_at": payload.get("issued_at"),
        }
        self._save_record(record)
        return record

    def _validate_expiry(self, payload: dict) -> None:
        expires_at = payload.get("expires_at")
        if expires_at is not None and _parse_time(str(expires_at)) <= datetime.now(timezone.utc):
            raise LicenseError("This WARAKA license has expired.")

    def _save_record(self, record: dict) -> None:
        try:
            protected = _dpapi_transform(
                json.dumps(record, separators=(",", ":")).encode("utf-8"),
                protect=True,
            )
            self.license_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.license_path.with_suffix(".tmp")
            temp_path.write_bytes(protected)
            os.replace(temp_path, self.license_path)
        except LicenseError:
            raise
        except Exception as exc:
            raise LicenseError("Could not securely save the WARAKA license on this Windows account.") from exc

    def load_record(self) -> dict | None:
        if not self.license_path.exists():
            return None
        try:
            raw = _dpapi_transform(self.license_path.read_bytes(), protect=False)
            record = json.loads(raw.decode("utf-8"))
            payload = record["license"]
            verify_license_signature(payload, record["signature"], self.public_key_b64)
            if payload.get("device_id") != self.device_id:
                raise LicenseError("The saved license belongs to another device.")
            self._validate_expiry(payload)
            return record
        except LicenseError:
            raise
        except Exception as exc:
            raise LicenseError("The local WARAKA license data could not be verified.") from exc

    def check_status(self) -> dict | None:
        record = self.load_record()
        if not record:
            return None
        payload = record["license"]
        last_verified = _parse_time(str(record.get("last_verified_at") or payload["issued_at"]))
        elapsed_days = max(0, (datetime.now(timezone.utc) - last_verified).total_seconds() / 86400)
        recheck_days = int(payload.get("recheck_days", 7))
        offline_grace_days = int(payload.get("offline_grace_days", 14))
        if elapsed_days >= recheck_days:
            try:
                result = self._request(
                    "/v1/license/verify",
                    {
                        "serial": record["serial"],
                        "email": record["email"],
                        "device_id": self.device_id,
                    },
                )
                if result.get("valid") is not True or not result.get("server_time"):
                    raise LicenseError("The licensing server did not validate this device.", 403)
                record["last_verified_at"] = result["server_time"]
                self._save_record(record)
            except LicenseError as exc:
                if exc.status_code is not None and exc.status_code < 500 and exc.status_code not in {408, 425, 429}:
                    raise
                if elapsed_days > offline_grace_days:
                    raise LicenseError("The 14-day offline grace period has ended. Connect to the internet to verify WARAKA.") from exc
        return record

    def deactivate(self) -> None:
        record = self.load_record()
        if not record:
            return
        self._request(
            "/v1/license/deactivate",
            {
                "serial": record["serial"],
                "email": record["email"],
                "device_id": self.device_id,
            },
        )
        try:
            self.license_path.unlink(missing_ok=True)
        except OSError as exc:
            raise LicenseError("The device was deactivated, but the local license file could not be removed.") from exc
