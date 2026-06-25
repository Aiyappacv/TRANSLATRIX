import secrets
from datetime import datetime, timedelta, timezone
import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.modules.frontend_api.security import get_frontend_user as get_current_user
from app.modules.auth.schemas import LoginRequest
from app.modules.auth.service import AuthService
from app.modules.companies.repository import CompanyRepository
from app.modules.frontend_api.store import get_state, set_state
from app.modules.frontend_api.security_policy import (
    client_ip_allowed,
    password_is_expired,
    security_settings_for_user,
    scope_for_identity,
    validate_password_against_policy,
)
from app.modules.frontend_api.events import append_audit
from app.modules.frontend_api.utils import new_id, now_iso, user_dto
from app.modules.frontend_api.mfa import create_challenge, consume_challenge, mfa_is_required, profile_enabled
from app.modules.tenants.models import TenantStatus
from app.modules.tenants.repository import TenantRepository
from app.modules.users.models import User as UserModel
from app.modules.users.repository import RoleRepository, UserRepository
from app.core.jwt import create_access_token, create_refresh_token, decode_token
from app.config import settings
from app.core.security import hash_password, verify_password

logger = structlog.get_logger(__name__)

router = APIRouter()


def _session_payload(db: Session, user, policy: dict | None = None) -> dict:
    policy = policy or security_settings_for_user(db, user)
    timeout_minutes = max(5, min(int(policy.get("sessionTimeoutMinutes") or 30), 1440))
    token_data = {"sub": str(user.id), "email": user.email}
    payload = user_dto(user, mfa_enabled=profile_enabled(db, str(user.id)))
    return {
        "accessToken": create_access_token(token_data, expires_delta=timedelta(minutes=timeout_minutes)),
        "refreshToken": create_refresh_token(token_data),
        "expiresIn": timeout_minutes * 60,
        "mfaRequired": False,
        "user": payload,
    }


@router.post("/auth/login")
def login(request_http: Request, payload: dict = Body(...), db: Session = Depends(get_db)):
    try:
        email = (payload.get("email", "") or "").strip().lower()
        password = payload.get("password", "")
        request = LoginRequest(email=email, password=password)
        user = db.query(UserModel).filter(func.lower(UserModel.email) == email).first()
        if user is None or not verify_password(request.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not user.is_active:
            raise HTTPException(status_code=401, detail="Account is inactive")
        UserRepository(db).update_last_login(user.id)
        policy = security_settings_for_user(db, user)
        forwarded = request_http.headers.get("x-forwarded-for", "").split(",")[0].strip()
        client_ip = forwarded or (request_http.client.host if request_http.client else None)
        if not client_ip_allowed(client_ip, str(policy.get("allowedIpRanges") or "")):
            raise HTTPException(status_code=403, detail="Sign-in is not allowed from this IP address")
        if password_is_expired(user, policy):
            raise HTTPException(status_code=403, detail="Password expired. Reset your password before signing in.")
        scope = scope_for_identity(user)
        mfa_required = mfa_is_required(policy, user) or profile_enabled(db, str(user.id))
        development_bypass = settings.is_development() and settings.DEV_DISABLE_MFA
        if mfa_required and not development_bypass:
            challenge = create_challenge(db, user)
            append_audit(db, scope, user, "MFA_CHALLENGE_CREATED", "user", str(user.id), new_value={"email": user.email, "setupRequired": challenge["mfaSetupRequired"], "clientIp": client_ip})
            return challenge
        if mfa_required and development_bypass:
            append_audit(db, scope, user, "MFA_BYPASSED_DEVELOPMENT", "user", str(user.id), new_value={"email": user.email, "clientIp": client_ip})
        append_audit(db, scope, user, "USER_LOGIN", "user", str(user.id), new_value={"email": user.email, "clientIp": client_ip})
        return _session_payload(db, user, policy)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("login_unexpected_error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred. Please try again.") from exc


@router.post("/auth/mfa/verify")
def verify_mfa(payload: dict = Body(...), db: Session = Depends(get_db)):
    challenge_token = str(payload.get("challengeToken") or payload.get("challenge_token") or "")
    code = str(payload.get("code") or "")
    if not challenge_token or not code:
        raise HTTPException(status_code=422, detail="challengeToken and code are required")
    user_id = consume_challenge(db, challenge_token, code)
    user = UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    scope = scope_for_identity(user)
    append_audit(db, scope, user, "MFA_VERIFIED", "user", str(user.id), new_value={"email": user.email})
    return _session_payload(db, user)


@router.post("/auth/mfa/setup")
def setup_mfa(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    challenge = create_challenge(db, current_user, setup=True)
    scope = scope_for_identity(current_user)
    append_audit(db, scope, current_user, "MFA_SETUP_STARTED", "user", str(current_user.id))
    return challenge


@router.post("/auth/refresh")
def refresh(payload: dict = Body(...), db: Session = Depends(get_db)):
    token = payload.get("refreshToken") or payload.get("refresh_token")
    if not token:
        raise HTTPException(status_code=400, detail="refreshToken is required")
    try:
        decoded = decode_token(token) or {}
        if decoded.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        user = UserRepository(db).get_by_id(str(decoded.get("sub") or ""))
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        policy = security_settings_for_user(db, user)
        if password_is_expired(user, policy):
            raise HTTPException(status_code=403, detail="Password expired. Reset your password before continuing.")
        timeout_minutes = max(5, min(int(policy.get("sessionTimeoutMinutes") or 30), 1440))
        access_token = create_access_token(
            {"sub": str(user.id), "email": user.email},
            expires_delta=timedelta(minutes=timeout_minutes),
        )
        return {"accessToken": access_token, "refreshToken": token, "expiresIn": timeout_minutes * 60}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("refresh_unexpected_error")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again.") from exc


@router.get("/auth/me")
def me(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return user_dto(current_user, mfa_enabled=profile_enabled(db, str(current_user.id)))


@router.post("/auth/forgot-password")
def forgot_password(payload: dict = Body(...), db: Session = Depends(get_db)):
    email = str(payload.get("email", "")).strip().lower()
    # Always return the same response to avoid account enumeration.
    user = UserRepository(db).get_by_email(email) if email else None
    if user:
        tokens = get_state(db, "platform", "password_reset_tokens", {})
        tokens[secrets.token_urlsafe(24)] = {"userId": str(user.id), "createdAt": now_iso()}
        set_state(db, "platform", "password_reset_tokens", tokens)
    return {"status": "accepted"}


@router.post("/auth/reset-password")
def reset_password(payload: dict = Body(...), db: Session = Depends(get_db)):
    token = str(payload.get("token", ""))
    password = str(payload.get("password") or payload.get("new_password") or "")
    tokens = get_state(db, "platform", "password_reset_tokens", {})
    token_data = tokens.get(token)
    if not token_data:
        raise HTTPException(status_code=400, detail="Reset token is invalid or expired")
    try:
        created_at = datetime.fromisoformat(str(token_data.get("createdAt", "")).replace("Z", "+00:00"))
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - created_at).total_seconds()
    except (TypeError, ValueError):
        age_seconds = 1801
    if age_seconds > 1800:
        tokens.pop(token, None)
        set_state(db, "platform", "password_reset_tokens", tokens)
        raise HTTPException(status_code=400, detail="Reset token is invalid or expired")
    user = UserRepository(db).get_by_id(token_data["userId"])
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    errors = validate_password_against_policy(password, security_settings_for_user(db, user))
    if errors:
        raise HTTPException(status_code=422, detail=" ".join(errors))
    UserRepository(db).update_password(user.id, hash_password(password))
    tokens.pop(token, None)
    set_state(db, "platform", "password_reset_tokens", tokens)
    scope = scope_for_identity(user)
    append_audit(db, scope, user, "PASSWORD_RESET", "user", str(user.id))
    return {"status": "reset"}


@router.post("/auth/change-password")
def change_password(
    payload: dict = Body(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_password = str(payload.get("currentPassword") or payload.get("current_password") or "")
    new_password = str(payload.get("newPassword") or payload.get("new_password") or "")
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(status_code=422, detail="Current password is incorrect")
    errors = validate_password_against_policy(new_password, security_settings_for_user(db, current_user))
    if errors:
        raise HTTPException(status_code=422, detail=" ".join(errors))
    UserRepository(db).update_password(current_user.id, hash_password(new_password))
    scope = scope_for_identity(current_user)
    append_audit(db, scope, current_user, "PASSWORD_CHANGED", "user", str(current_user.id))
    return {"status": "changed"}


@router.post("/register", status_code=201)
def register_company(payload: dict = Body(...), db: Session = Depends(get_db)):
    email = str(payload.get("primaryContactEmail", "")).strip().lower()
    legal_name = str(payload.get("legalName", "")).strip()
    if not legal_name or not email:
        raise HTTPException(status_code=422, detail="Company name and primary contact email are required")
    if CompanyRepository(db).get_by_email(email):
        raise HTTPException(status_code=409, detail="A company with this email already exists")

    user_repo = UserRepository(db)
    if user_repo.get_by_email(email):
        raise HTTPException(status_code=409, detail="A user with this email already exists")

    tenant = TenantRepository(db).create(name=legal_name, plan="starter")
    tenant.status = TenantStatus.INACTIVE
    db.commit()
    db.refresh(tenant)
    company = CompanyRepository(db).create(
        tenant_id=tenant.id,
        legal_name=legal_name,
        trading_name=payload.get("tradingName"),
        country=payload.get("country") or "Unknown",
        industry=payload.get("industry"),
        registration_number=payload.get("registrationNumber"),
        tax_number=payload.get("taxId"),
        primary_contact=payload.get("primaryContactName"),
        email=email,
        phone=payload.get("phoneNumber"),
        website=payload.get("website"),
        default_currency=payload.get("defaultCurrency") or "USD",
        default_language=payload.get("defaultLanguage") or "en",
        timezone=payload.get("timezone") or "UTC",
    )

    role_repo = RoleRepository(db)
    role = role_repo.get_by_name("company_admin")
    if role is None:
        role = role_repo.create("company_admin", "Company Admin", "Company administrator", True)
    parts = str(payload.get("primaryContactName") or "Company Admin").split(maxsplit=1)
    user_repo.create(
        email=email,
        hashed_password=hash_password(secrets.token_urlsafe(18)),
        tenant_id=tenant.id,
        company_id=company.id,
        role_id=role.id,
        first_name=parts[0],
        last_name=parts[1] if len(parts) > 1 else "",
        is_active=False,
        is_email_verified=False,
    )
    requests = get_state(db, "platform", "registration_requests", [])
    requests.insert(0, {"id": new_id("registration"), "companyId": str(company.id), "email": email, "payload": payload, "status": "pending", "createdAt": now_iso()})
    set_state(db, "platform", "registration_requests", requests)
    return {"id": str(company.id), "status": "pending", "payload": payload}
