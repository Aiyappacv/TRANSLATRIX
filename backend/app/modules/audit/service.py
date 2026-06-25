"""
Audit Service
Business logic for audit logging and querying
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import structlog

from app.modules.audit.models import AuditLog
from app.modules.super_admin.models import SuperAdminAuditLog

logger = structlog.get_logger(__name__)


class AuditService:
    """Service for audit logging"""

    @staticmethod
    def create_audit_log(
        db: Session,
        tenant_id: UUID,
        entity_type: str,
        entity_id: str,
        action: str,
        user_id: Optional[UUID] = None,
        description: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Create audit log entry"""
        audit_log = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            description=description,
            old_value=old_value,
            new_value=new_value,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent
        )

        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)

        logger.info(
            "audit_log_created",
            tenant_id=str(tenant_id),
            entity_type=entity_type,
            action=action
        )

        return audit_log

    @staticmethod
    def query_audit_logs(
        db: Session,
        tenant_id: UUID,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        action: Optional[str] = None,
        user_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[AuditLog], int]:
        """Query audit logs with filters"""
        query = db.query(AuditLog).filter(AuditLog.tenant_id == tenant_id)

        # Apply filters
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)

        if entity_id:
            query = query.filter(AuditLog.entity_id == entity_id)

        if action:
            query = query.filter(AuditLog.action == action)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)

        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

        return logs, total

    @staticmethod
    def get_entity_history(
        db: Session,
        tenant_id: UUID,
        entity_type: str,
        entity_id: str
    ) -> List[AuditLog]:
        """Get complete history for an entity"""
        logs = db.query(AuditLog).filter(
            and_(
                AuditLog.tenant_id == tenant_id,
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id
            )
        ).order_by(AuditLog.created_at).all()

        return logs

    @staticmethod
    def create_super_admin_audit_log(
        db: Session,
        admin_user_id: UUID,
        action: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        description: Optional[str] = None,
        reason: Optional[str] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> SuperAdminAuditLog:
        """Create super admin audit log"""
        audit_log = SuperAdminAuditLog(
            admin_user_id=admin_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            description=description,
            reason=reason,
            request_id=request_id,
            ip_address=ip_address
        )

        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)

        logger.info(
            "super_admin_audit_log_created",
            admin_user_id=str(admin_user_id),
            action=action
        )

        return audit_log
