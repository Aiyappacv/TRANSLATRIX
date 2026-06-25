import secrets
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.modules.frontend_api.security import get_frontend_user as get_current_user, get_selected_company_id, require_frontend_permission
from app.modules.companies.models import Company
from app.modules.companies.repository import CompanyRepository
from app.modules.frontend_api.defaults import BACKEND_ROLE_TO_FRONTEND, COMPANY_SETTINGS
from app.modules.frontend_api.events import append_audit
from app.modules.frontend_api.store import get_state, scope_for_user, set_state
from app.modules.frontend_api.utils import company_dto, company_user_dto, frontend_role, new_id, now_iso
from app.modules.users.models import Role, User
from app.modules.users.repository import RoleRepository, UserRepository
from app.core.security import hash_password

router = APIRouter()


@router.get("/companies")
def companies(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Company)
    if not current_user.is_super_admin:
        query = query.filter(Company.tenant_id == current_user.tenant_id)
    return [company_dto(c) for c in query.order_by(Company.created_at.desc()).all()]


@router.get("/companies/current")
def current_company(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    selected_company_id = get_selected_company_id(current_user)
    if selected_company_id:
        company = db.query(Company).filter(Company.id == selected_company_id).first()
    else:
        company = db.query(Company).order_by(Company.created_at.asc()).first()
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return company_dto(company)


@router.get("/users")
def users(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(User)
    selected_company_id = get_selected_company_id(current_user)
    if selected_company_id:
        query = query.filter(User.company_id == selected_company_id)
    elif not current_user.is_super_admin:
        query = query.filter(User.company_id == current_user.company_id)
    return [company_user_dto(u) for u in query.order_by(User.created_at.desc()).all()]


@router.post("/users/invitations", status_code=201, dependencies=[Depends(require_frontend_permission("users:manage"))])
def invite_user(payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    email = str(payload.get("email", "")).strip().lower()
    if not email:
        raise HTTPException(status_code=422, detail="Email is required")
    if UserRepository(db).get_by_email(email):
        raise HTTPException(status_code=409, detail="A user with this email already exists")
    company_id = payload.get("companyId") or str(get_selected_company_id(current_user) or "")
    company = CompanyRepository(db).get_by_id(company_id) if company_id else None
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if not current_user.is_super_admin and company.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Company access denied")
    requested_role = str(payload.get("role") or "read_only")
    backend_role = requested_role
    role = RoleRepository(db).get_by_name(backend_role)
    if role is None:
        role = RoleRepository(db).create(backend_role, backend_role.replace("_", " ").title(), "Frontend role", True)
    name = str(payload.get("name") or email).strip()
    parts = name.split(maxsplit=1)
    user = UserRepository(db).create(
        email=email,
        hashed_password=hash_password(secrets.token_urlsafe(18)),
        tenant_id=company.tenant_id,
        company_id=company.id,
        role_id=role.id,
        first_name=parts[0],
        last_name=parts[1] if len(parts) > 1 else "",
        department=payload.get("department") or "",
        is_active=False,
        is_email_verified=False,
    )
    dto = company_user_dto(user)
    dto["status"] = "invited"
    append_audit(db, scope_for_user(current_user), current_user, "USER_INVITED", "user", str(user.id), new_value={"email": email, "role": requested_role, "companyId": str(company.id)})
    return dto


@router.patch("/users/{user_id}/role", dependencies=[Depends(require_frontend_permission("users:manage"))])
def change_role(user_id: str, payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    target = UserRepository(db).get_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not current_user.is_super_admin and target.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="User access denied")
    role_name = str(payload.get("role") or "read_only")
    role = RoleRepository(db).get_by_name(role_name)
    if role is None:
        role = RoleRepository(db).create(role_name, role_name.replace("_", " ").title(), "Frontend role", True)
    previous_role = getattr(getattr(target, "role", None), "name", None)
    target.role_id = role.id
    db.commit(); db.refresh(target)
    append_audit(db, scope_for_user(current_user), current_user, "USER_ROLE_CHANGED", "user", user_id, old_value={"role": previous_role}, new_value={"role": role_name})
    return company_user_dto(target)


@router.patch("/users/{user_id}/status", dependencies=[Depends(require_frontend_permission("users:manage"))])
def change_status(user_id: str, payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    target = UserRepository(db).get_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not current_user.is_super_admin and target.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="User access denied")
    value = str(payload.get("status") or "disabled")
    previous = "active" if target.is_active else "disabled"
    target.is_active = value == "active"
    db.commit(); db.refresh(target)
    dto = company_user_dto(target)
    dto["status"] = value
    append_audit(db, scope_for_user(current_user), current_user, "USER_STATUS_CHANGED", "user", user_id, old_value={"status": previous}, new_value={"status": value})
    return dto


@router.get("/settings/company", dependencies=[Depends(require_frontend_permission("settings:manage"))])
def get_company_settings(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    selected_company_id = get_selected_company_id(current_user)
    company = db.query(Company).filter(Company.id == selected_company_id).first() if selected_company_id else None
    default = dict(COMPANY_SETTINGS)
    if company:
        default.update({"legalName": company.legal_name, "tradingName": company.trading_name or "", "country": company.country, "industry": company.industry or "", "registrationNumber": company.registration_number or "", "taxId": company.tax_number or "", "defaultCurrency": company.default_currency or "USD", "defaultLanguage": company.default_language or "en", "timezone": company.timezone or "UTC", "financeContact": company.email, "website": company.website or "", "phone": company.phone or ""})
    return get_state(db, scope_for_user(current_user), "settings_company", default)


@router.put("/settings/company", dependencies=[Depends(require_frontend_permission("settings:manage"))])
def save_company_settings(payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    selected_company_id = get_selected_company_id(current_user)
    company = db.query(Company).filter(Company.id == selected_company_id).first() if selected_company_id else None
    scope = scope_for_user(current_user)
    previous = get_state(db, scope, "settings_company", {})
    if company:
        mapping = {"legalName": "legal_name", "tradingName": "trading_name", "country": "country", "industry": "industry", "registrationNumber": "registration_number", "taxId": "tax_number", "defaultCurrency": "default_currency", "defaultLanguage": "default_language", "timezone": "timezone", "financeContact": "email", "website": "website", "phone": "phone"}
        for src, dest in mapping.items():
            if src in payload: setattr(company, dest, payload[src])
        db.commit()
    result = set_state(db, scope, "settings_company", payload)
    append_audit(db, scope, current_user, "COMPANY_SETTINGS_UPDATED", "company", str(selected_company_id or "current"), old_value=previous, new_value=payload)
    return result
