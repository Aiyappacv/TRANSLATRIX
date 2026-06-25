"""
User Repository
Database operations for users and roles
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from uuid import UUID

from app.modules.users.models import User, Role


class RoleRepository:
    """Repository for role database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str, display_name: str, description: Optional[str] = None, is_system_role: bool = False) -> Role:
        """Create a new role"""
        role = Role(
            name=name,
            display_name=display_name,
            description=description,
            is_system_role=is_system_role
        )
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

    def get_by_id(self, role_id: str | UUID) -> Optional[Role]:
        """Get role by ID"""
        if isinstance(role_id, str):
            role_id = UUID(role_id)
        return self.db.query(Role).filter(Role.id == role_id).first()

    def get_by_name(self, name: str) -> Optional[Role]:
        """Get role by name"""
        return self.db.query(Role).filter(Role.name == name).first()

    def get_all(self) -> List[Role]:
        """Get all roles"""
        return self.db.query(Role).all()


class UserRepository:
    """Repository for user database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        email: str,
        hashed_password: str,
        tenant_id: Optional[str | UUID] = None,
        company_id: Optional[str | UUID] = None,
        role_id: Optional[str | UUID] = None,
        **kwargs
    ) -> User:
        """Create a new user"""
        if isinstance(tenant_id, str):
            tenant_id = UUID(tenant_id)
        if isinstance(company_id, str):
            company_id = UUID(company_id)
        if isinstance(role_id, str):
            role_id = UUID(role_id)

        user = User(
            email=email,
            hashed_password=hashed_password,
            tenant_id=tenant_id,
            company_id=company_id,
            role_id=role_id,
            **kwargs
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: str | UUID) -> Optional[User]:
        """Get user by ID"""
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()

    def get_by_tenant_id(self, tenant_id: str | UUID) -> List[User]:
        """Get all users for a tenant"""
        if isinstance(tenant_id, str):
            tenant_id = UUID(tenant_id)
        return self.db.query(User).filter(User.tenant_id == tenant_id).all()

    def get_by_company_id(self, company_id: str | UUID) -> List[User]:
        """Get all users for a company"""
        if isinstance(company_id, str):
            company_id = UUID(company_id)
        return self.db.query(User).filter(User.company_id == company_id).all()

    def update(self, user_id: str | UUID, **kwargs) -> Optional[User]:
        """Update user"""
        user = self.get_by_id(user_id)
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            self.db.commit()
            self.db.refresh(user)
        return user

    def update_password(self, user_id: str | UUID, hashed_password: str) -> Optional[User]:
        """Update user password"""
        from datetime import datetime
        user = self.get_by_id(user_id)
        if user:
            user.hashed_password = hashed_password
            user.password_changed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(user)
        return user

    def update_last_login(self, user_id: str | UUID) -> Optional[User]:
        """Update last login timestamp"""
        from datetime import datetime
        user = self.get_by_id(user_id)
        if user:
            user.last_login = datetime.utcnow()
            user.failed_login_attempts = 0
            self.db.commit()
            self.db.refresh(user)
        return user
