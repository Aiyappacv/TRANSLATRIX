"""Create safe local-development accounts for every frontend role.

This script refuses to run when APP_ENV=production. It is idempotent and does
not create example financial documents, entries, batches, or postings.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.core.security import hash_password
from app.database import SessionLocal, init_db
from app.modules.companies.repository import CompanyRepository
from app.modules.tenants.repository import TenantRepository
from app.modules.users.repository import RoleRepository, UserRepository

PASSWORD = os.getenv("DEV_SEED_PASSWORD", "DevOnly!2026")

ROLE_ACCOUNTS = [
    ("company_owner", "owner@translatrix.example.com", "Company", "Owner"),
    ("company_admin", "admin@translatrix.example.com", "Company", "Admin"),
    ("finance_manager", "finance.manager@translatrix.example.com", "Finance", "Manager"),
    ("finance_user", "finance.user@translatrix.example.com", "Finance", "User"),
    ("reviewer", "reviewer@translatrix.example.com", "Review", "User"),
    ("approver", "approver@translatrix.example.com", "Approval", "User"),
    ("sap_poster", "sap.poster@translatrix.example.com", "SAP", "Poster"),
    ("integration_manager", "integrations@translatrix.example.com", "Integration", "Manager"),
    ("auditor", "auditor@translatrix.example.com", "Audit", "User"),
    ("read_only", "readonly@translatrix.example.com", "Read", "Only"),
]


def ensure_role(db, name: str):
    repo = RoleRepository(db)
    return repo.get_by_name(name) or repo.create(name, name.replace("_", " ").title(), "Development test role", True)


def main() -> None:
    if settings.is_production():
        raise SystemExit("Development seed is disabled in production.")
    init_db()
    db = SessionLocal()
    try:
        tenant_repo = TenantRepository(db)
        company_repo = CompanyRepository(db)
        user_repo = UserRepository(db)

        tenant = tenant_repo.get_by_name("TRANSLATRIX Development Tenant")
        if tenant is None:
            tenant = tenant_repo.create("TRANSLATRIX Development Tenant", "enterprise")
        company = company_repo.get_by_email("company@translatrix.example.com")
        if company is None:
            company = company_repo.create(
                tenant_id=tenant.id,
                legal_name="TRANSLATRIX Development Company",
                trading_name="Development Company",
                country="IN",
                industry="Software Testing",
                email="company@translatrix.example.com",
                default_currency="INR",
                default_language="en",
                timezone="Asia/Kolkata",
            )

        super_role = ensure_role(db, "super_admin")
        super_email = "super.admin@translatrix.example.com"
        super_user = user_repo.get_by_email(super_email)
        if super_user is None:
            user_repo.create(
                email=super_email,
                hashed_password=hash_password(PASSWORD),
                role_id=super_role.id,
                first_name="Platform",
                last_name="Admin",
                is_active=True,
                is_super_admin=True,
                is_email_verified=True,
            )
        else:
            user_repo.update_password(super_user.id, hash_password(PASSWORD))

        for role_name, email, first_name, last_name in ROLE_ACCOUNTS:
            role = ensure_role(db, role_name)
            user = user_repo.get_by_email(email)
            if user is None:
                user_repo.create(
                    email=email,
                    hashed_password=hash_password(PASSWORD),
                    tenant_id=tenant.id,
                    company_id=company.id,
                    role_id=role.id,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True,
                    is_email_verified=True,
                )
            else:
                user_repo.update(user.id, role_id=role.id, tenant_id=tenant.id, company_id=company.id, is_active=True, is_email_verified=True)
                user_repo.update_password(user.id, hash_password(PASSWORD))

        print("Development accounts are ready. No example business data was created.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
