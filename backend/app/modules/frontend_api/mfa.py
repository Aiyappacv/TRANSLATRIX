from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.frontend_api.store import get_state, set_state
from app.modules.frontend_api.utils import frontend_role

PRIVILEGED_ROLES = {
    "spectra_super_admin",
    "company_owner",
    "company_admin",
    "finance_manager",
    "approver",
    "sap_poster",
    "integration_manager",
}


def mfa_is_required(policy: dict, user) -> bool:
    if bool(policy.get("mfaRequired")):
        return True
    return bool(policy.get("mfaRequiredForPrivilegedRoles")) and frontend_role(user) in PRIVILEGED_ROLES


def _profiles(db: Session) -> dict:
    return get_state(db, "platform", "mfa_profiles", {})


def get_profile(db: Session, user_id: str) -> dict | None:
    return _profiles(db).get(str(user_id))


def profile_enabled(db: Session, user_id: str) -> bool:
    return bool((get_profile(db, user_id) or {}).get("enabled"))


def _new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _decode_secret(secret: str) -> bytes:
    normalized = secret.strip().replace(" ", "").upper()
    normalized += "=" * ((8 - len(normalized) % 8) % 8)
    return base64.b32decode(normalized, casefold=True)


def totp_code(secret: str, for_time: int | None = None, interval: int = 30, digits: int = 6) -> str:
    timestamp = int(for_time if for_time is not None else time.time())
    counter = timestamp // interval
    digest = hmac.new(_decode_secret(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(value).zfill(digits)


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    candidate = "".join(ch for ch in str(code) if ch.isdigit())
    if len(candidate) != 6:
        return False
    now = int(time.time())
    return any(hmac.compare_digest(totp_code(secret, now + step * 30), candidate) for step in range(-window, window + 1))


def _challenge_store(db: Session) -> dict:
    return get_state(db, "platform", "mfa_challenges", {})


def create_challenge(db: Session, user, setup: bool = False) -> dict:
    profiles = _profiles(db)
    user_id = str(user.id)
    profile = profiles.get(user_id)
    if profile is None or setup:
        profile = {
            "secret": _new_secret(),
            "enabled": False,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "verifiedAt": None,
        }
        profiles[user_id] = profile
        set_state(db, "platform", "mfa_profiles", profiles)

    challenge_token = secrets.token_urlsafe(32)
    challenges = _challenge_store(db)
    challenges[challenge_token] = {
        "userId": user_id,
        "purpose": "setup" if not profile.get("enabled") else "verify",
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
    }
    set_state(db, "platform", "mfa_challenges", challenges)

    issuer = "TRANSLATRIX PRO"
    account = user.email
    uri = f"otpauth://totp/{quote(issuer)}:{quote(account)}?secret={profile['secret']}&issuer={quote(issuer)}&digits=6&period=30"
    result = {
        "mfaRequired": True,
        "mfaSetupRequired": not bool(profile.get("enabled")),
        "challengeToken": challenge_token,
        "expiresIn": 300,
        "email": user.email,
    }
    if not profile.get("enabled"):
        result.update({"secret": profile["secret"], "otpauthUri": uri})
    return result


def consume_challenge(db: Session, challenge_token: str, code: str):
    challenges = _challenge_store(db)
    challenge = challenges.get(challenge_token)
    if not challenge:
        raise HTTPException(status_code=400, detail="MFA challenge is invalid or expired")
    try:
        expires_at = datetime.fromisoformat(str(challenge["expiresAt"]).replace("Z", "+00:00"))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    except (KeyError, TypeError, ValueError):
        expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    if expires_at < datetime.now(timezone.utc):
        challenges.pop(challenge_token, None)
        set_state(db, "platform", "mfa_challenges", challenges)
        raise HTTPException(status_code=400, detail="MFA challenge is invalid or expired")

    profiles = _profiles(db)
    profile = profiles.get(str(challenge.get("userId")))
    if not profile or not verify_totp(str(profile.get("secret") or ""), code):
        raise HTTPException(status_code=422, detail="The verification code is invalid")

    profile["enabled"] = True
    profile["verifiedAt"] = datetime.now(timezone.utc).isoformat()
    profiles[str(challenge["userId"])] = profile
    set_state(db, "platform", "mfa_profiles", profiles)
    challenges.pop(challenge_token, None)
    set_state(db, "platform", "mfa_challenges", challenges)
    return str(challenge["userId"])
