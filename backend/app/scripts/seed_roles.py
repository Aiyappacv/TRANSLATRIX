"""
Seed Roles Script
Creates default system roles for TRANSLATRIX PRO
Run this script before starting the application for the first time
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.modules.users.models import Role
from app.modules.users.repository import RoleRepository
import structlog

logger = structlog.get_logger(__name__)


# Define default roles
DEFAULT_ROLES = [
    {
        "name": "super_admin",
        "display_name": "Super Administrator",
        "description": "Platform administrator with full access to all tenants and companies",
        "is_system_role": True
    },
    {
        "name": "company_admin",
        "display_name": "Company Administrator",
        "description": "Full administrative access to company settings, users, and all features",
        "is_system_role": True
    },
    {
        "name": "company_finance_manager",
        "display_name": "Finance Manager",
        "description": "Manage financial configurations, approve entries, and configure integrations",
        "is_system_role": True
    },
    {
        "name": "company_reviewer",
        "display_name": "Reviewer",
        "description": "Review and approve document translations and accounting entries",
        "is_system_role": True
    },
    {
        "name": "company_approver",
        "display_name": "Approver",
        "description": "Final approval authority for accounting entries before posting",
        "is_system_role": True
    },
    {
        "name": "company_viewer",
        "display_name": "Viewer",
        "description": "Read-only access to view documents and entries",
        "is_system_role": True
    }
]


def create_tables():
    """Create all database tables"""
    logger.info("creating_database_tables")
    Base.metadata.create_all(bind=engine)
    logger.info("database_tables_created")


def seed_roles(db: Session):
    """
    Seed default roles into the database

    Args:
        db: Database session
    """
    role_repo = RoleRepository(db)

    logger.info("seeding_roles", count=len(DEFAULT_ROLES))

    created_count = 0
    updated_count = 0
    skipped_count = 0

    for role_data in DEFAULT_ROLES:
        try:
            # Check if role already exists
            existing_role = role_repo.get_by_name(role_data["name"])

            if existing_role:
                logger.info(
                    "role_already_exists",
                    name=role_data["name"],
                    role_id=str(existing_role.id)
                )
                skipped_count += 1
            else:
                # Create new role
                role = role_repo.create(
                    name=role_data["name"],
                    display_name=role_data["display_name"],
                    description=role_data["description"],
                    is_system_role=role_data["is_system_role"]
                )
                logger.info(
                    "role_created",
                    name=role_data["name"],
                    role_id=str(role.id)
                )
                created_count += 1

        except Exception as e:
            logger.error(
                "role_creation_failed",
                name=role_data["name"],
                error=str(e)
            )
            continue

    logger.info(
        "roles_seeding_completed",
        created=created_count,
        updated=updated_count,
        skipped=skipped_count,
        total=len(DEFAULT_ROLES)
    )

    return {
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "total": len(DEFAULT_ROLES)
    }


def verify_roles(db: Session):
    """
    Verify all roles were created successfully

    Args:
        db: Database session
    """
    role_repo = RoleRepository(db)
    all_roles = role_repo.get_all()

    logger.info("verifying_roles", total_roles=len(all_roles))

    print("\n" + "=" * 80)
    print("ROLES IN DATABASE")
    print("=" * 80)

    for role in all_roles:
        print(f"\nRole: {role.name}")
        print(f"  Display Name: {role.display_name}")
        print(f"  Description: {role.description}")
        print(f"  System Role: {role.is_system_role}")
        print(f"  ID: {role.id}")

    print("\n" + "=" * 80)
    print(f"Total Roles: {len(all_roles)}")
    print("=" * 80 + "\n")


def main():
    """Main function to seed roles"""
    print("\n" + "=" * 80)
    print("TRANSLATRIX PRO - Seed Roles Script")
    print("=" * 80 + "\n")

    # Create tables
    create_tables()

    # Create database session
    db = SessionLocal()

    try:
        # Seed roles
        result = seed_roles(db)

        print("\n" + "-" * 80)
        print("SEEDING RESULTS")
        print("-" * 80)
        print(f"Created: {result['created']}")
        print(f"Skipped (already exists): {result['skipped']}")
        print(f"Total roles: {result['total']}")
        print("-" * 80 + "\n")

        # Verify roles
        verify_roles(db)

        print("\n" + "=" * 80)
        print("SUCCESS: Roles seeded successfully!")
        print("=" * 80 + "\n")

    except Exception as e:
        logger.error("seeding_failed", error=str(e))
        print(f"\nERROR: Seeding failed: {e}\n")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
