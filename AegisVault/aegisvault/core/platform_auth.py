"""Optional Windows Hello / fingerprint verification helpers.

The vault password remains the encryption secret. This module only asks the
operating system to verify the current Windows user before sensitive actions.
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PlatformAuthStatus:
    available: bool
    message: str


def _load_user_consent_verifier() -> Any:
    try:
        from winsdk.windows.security.credentials.ui import UserConsentVerifier

        return UserConsentVerifier
    except Exception:
        pass

    try:
        from winrt.windows.security.credentials.ui import UserConsentVerifier

        return UserConsentVerifier
    except Exception as exc:
        raise RuntimeError(
            "Windows Hello support needs the optional Python WinRT bindings. "
            "Install the Windows-only dependency from requirements.txt."
        ) from exc


async def _await_operation(operation: Any) -> Any:
    return await operation


def _run_async(operation: Any) -> Any:
    try:
        return asyncio.run(_await_operation(operation))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_await_operation(operation))
        finally:
            loop.close()


def _enum_text(value: Any) -> str:
    name = getattr(value, "name", None)
    if name:
        return str(name).lower()
    return str(value).lower()


def _availability_message(result: Any) -> PlatformAuthStatus:
    text = _enum_text(result)
    if "available" in text and "not" not in text and "unavailable" not in text:
        return PlatformAuthStatus(True, "Windows Hello / fingerprint is available.")
    if "device_busy" in text or "devicebusy" in text:
        return PlatformAuthStatus(False, "The biometric device is busy.")
    if "device_not_present" in text or "devicenotpresent" in text:
        return PlatformAuthStatus(False, "No Windows Hello biometric device was found.")
    if "disabled_by_policy" in text or "disabledbypolicy" in text:
        return PlatformAuthStatus(False, "Windows Hello is disabled by policy.")
    if "not_configured" in text or "notconfigured" in text:
        return PlatformAuthStatus(False, "Windows Hello is not configured for this Windows user.")
    return PlatformAuthStatus(False, "Windows Hello / fingerprint is not available.")


def _verification_ok(result: Any) -> bool:
    text = _enum_text(result)
    return "verified" in text


def check_availability() -> PlatformAuthStatus:
    if not sys.platform.startswith("win"):
        return PlatformAuthStatus(False, "Windows Hello is only available on Windows.")
    try:
        verifier = _load_user_consent_verifier()
        result = _run_async(verifier.check_availability_async())
        return _availability_message(result)
    except Exception as exc:
        return PlatformAuthStatus(False, str(exc))


def verify_user(message: str = "Verify your identity to continue.") -> PlatformAuthStatus:
    if not sys.platform.startswith("win"):
        return PlatformAuthStatus(False, "Windows Hello is only available on Windows.")
    try:
        verifier = _load_user_consent_verifier()
        result = _run_async(verifier.request_verification_async(message))
        if _verification_ok(result):
            return PlatformAuthStatus(True, "Identity verified.")
        return PlatformAuthStatus(False, "Windows Hello verification was not completed.")
    except Exception as exc:
        return PlatformAuthStatus(False, str(exc))
