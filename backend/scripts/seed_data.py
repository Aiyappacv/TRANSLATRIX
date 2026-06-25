"""
Seed Data Script
Initialize database with default roles and super admin
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.core.security import hash_password
from app.config import settings
import structlog

# Import all models to ensure they are registered with SQLAlchemy
from app.modules.tenants.models import Tenant
from app.modules.companies.models import Company
from app.modules.users.models import User, Role
from app.modules.onboarding.models import CompanyOnboarding

# Import repositories after models
from app.modules.users.repository import RoleRepository, UserRepository

logger = structlog.get_logger()


def seed_roles(db):
    """Create default roles"""
    role_repo = RoleRepository(db)

    roles = [
        {
            "name": "super_admin",
            "display_name": "Super Admin",
            "description": "Platform administrator with full access",
            "is_system_role": True
        },
        {
            "name": "company_admin",
            "display_name": "Company Admin",
            "description": "Company administrator with full company access",
            "is_system_role": True
        },
        {
            "name": "finance_manager",
            "display_name": "Finance Manager",
            "description": "Finance manager with approval rights",
            "is_system_role": True
        },
        {
            "name": "accountant",
            "display_name": "Accountant",
            "description": "Accountant with review and entry management",
            "is_system_role": True
        },
        {
            "name": "reviewer",
            "display_name": "Reviewer",
            "description": "Reviewer for financial entries",
            "is_system_role": True
        },
        {
            "name": "viewer",
            "display_name": "Viewer",
            "description": "Read-only access to entries and analytics",
            "is_system_role": True
        }
    ]

    for role_data in roles:
        existing_role = role_repo.get_by_name(role_data["name"])
        if not existing_role:
            role = role_repo.create(**role_data)
            logger.info(f"Created role: {role.name}")
        else:
            logger.info(f"Role already exists: {role_data['name']}")

    return True


def seed_super_admin(db):
    """Create super admin user"""
    user_repo = UserRepository(db)
    role_repo = RoleRepository(db)

    # Check if super admin already exists
    existing_admin = user_repo.get_by_email(settings.SUPER_ADMIN_EMAIL)
    if existing_admin:
        logger.info(f"Super admin already exists: {settings.SUPER_ADMIN_EMAIL}")
        return True

    # Get super_admin role
    super_admin_role = role_repo.get_by_name("super_admin")
    if not super_admin_role:
        logger.error("Super admin role not found. Please seed roles first.")
        return False

    # Create super admin user
    hashed_password = hash_password(settings.SUPER_ADMIN_PASSWORD)
    admin_user = user_repo.create(
        email=settings.SUPER_ADMIN_EMAIL,
        hashed_password=hashed_password,
        role_id=super_admin_role.id,
        first_name="Super",
        last_name="Admin",
        is_active=True,
        is_super_admin=True,
        is_email_verified=True
    )

    logger.info(f"Created super admin: {admin_user.email}")
    return True


def main():
    """Run all seed functions"""
    logger.info("Starting database seeding...")

    db = SessionLocal()
    try:
        # Seed roles
        logger.info("Seeding roles...")
        if not seed_roles(db):
            logger.error("Failed to seed roles")
            return

        # Seed super admin
        logger.info("Seeding super admin...")
        if not seed_super_admin(db):
            logger.error("Failed to seed super admin")
            return

        logger.info("Database seeding completed successfully!")

    except Exception as e:
        logger.error(f"Error during seeding: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
