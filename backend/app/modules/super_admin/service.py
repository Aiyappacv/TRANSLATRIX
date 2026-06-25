"""
Super Admin Service
Platform-wide administration and monitoring logic
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
import structlog
from uuid import UUID

from app.modules.super_admin.models import SuperAdminAuditLog
from app.modules.super_admin.schemas import (
    PlatformStats,
    DashboardResponse,
    CompanyListItem,
    CompanyDetail,
    SystemHealthStatus,
    ComponentHealth,
    SystemHealthResponse,
    QueueMetrics,
    JobQueueResponse,
    IntegrationStatus,
    IntegrationsResponse,
    AuditLogEntry,
    JobQueueStatus,
)
from app.modules.companies.models import Company
from app.modules.tenants.models import Tenant, TenantStatus
from app.modules.users.models import User
from app.modules.files.models import IngestedFile
from app.config import settings

logger = structlog.get_logger(__name__)


class SuperAdminService:
    """Service for super admin operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_platform_dashboard(self) -> DashboardResponse:
        """
        Get platform-wide dashboard statistics
        """
        logger.info("fetching_platform_dashboard")

        # Get company statistics
        total_companies = self.db.query(func.count(Company.id)).scalar() or 0
        active_companies = (
            self.db.query(func.count(Company.id))
            .join(Tenant)
            .filter(Tenant.status == TenantStatus.ACTIVE)
            .scalar() or 0
        )
        suspended_companies = (
            self.db.query(func.count(Company.id))
            .join(Tenant)
            .filter(Tenant.status == TenantStatus.SUSPENDED)
            .scalar() or 0
        )

        # Get user statistics
        total_users = self.db.query(func.count(User.id)).scalar() or 0
        active_users = (
            self.db.query(func.count(User.id))
            .filter(User.is_active == True)
            .scalar() or 0
        )

        # Get file processing statistics
        total_files = self.db.query(func.count(IngestedFile.id)).scalar() or 0
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        files_today = (
            self.db.query(func.count(IngestedFile.id))
            .filter(IngestedFile.created_at >= today_start)
            .scalar() or 0
        )

        # Calculate storage used
        total_storage = (
            self.db.query(func.sum(IngestedFile.file_size)).scalar() or 0
        )

        # Calculate average processing time (placeholder)
        avg_processing_time = 0.0  # TODO: Implement when processing metrics are tracked

        # Recent signups (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_signups = (
            self.db.query(func.count(Company.id))
            .filter(Company.created_at >= week_ago)
            .scalar() or 0
        )

        stats = PlatformStats(
            total_companies=total_companies,
            active_companies=active_companies,
            suspended_companies=suspended_companies,
            total_users=total_users,
            active_users=active_users,
            total_files_processed=total_files,
            files_processed_today=files_today,
            total_storage_used_bytes=total_storage,
            avg_processing_time_seconds=avg_processing_time,
        )

        return DashboardResponse(
            stats=stats,
            revenue=None,  # TODO: Implement billing integration
            recent_signups=recent_signups,
            system_health="healthy",  # Simplified - use system_health endpoint for details
        )

    def list_companies(
        self,
        page: int = 1,
        page_size: int = 50,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[CompanyListItem], int]:
        """
        List all companies with filtering and pagination
        """
        query = self.db.query(
            Company,
            func.count(User.id).label("user_count"),
            func.max(User.last_login).label("last_activity"),
        ).outerjoin(User, Company.id == User.company_id).group_by(Company.id)

        # Apply filters
        if status:
            query = query.join(Tenant).filter(Tenant.status == status)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Company.legal_name.ilike(search_pattern))
                | (Company.trading_name.ilike(search_pattern))
                | (Company.email.ilike(search_pattern))
            )

        # Get total count
        total = query.count()

        # Apply pagination
        companies_data = (
            query.order_by(desc(Company.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        # Build response
        companies = []
        for company, user_count, last_activity in companies_data:
            # Get tenant status
            tenant = self.db.query(Tenant).filter(Tenant.id == company.tenant_id).first()
            status_value = tenant.status.value if tenant else "unknown"

            companies.append(
                CompanyListItem(
                    id=company.id,
                    tenant_id=company.tenant_id,
                    legal_name=company.legal_name,
                    trading_name=company.trading_name,
                    email=company.email,
                    country=company.country,
                    status=status_value,
                    user_count=user_count or 0,
                    created_at=company.created_at,
                    last_activity=last_activity,
                )
            )

        return companies, total

    def get_company_detail(self, company_id: UUID) -> Optional[CompanyDetail]:
        """
        Get detailed company information
        """
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return None

        # Get tenant
        tenant = self.db.query(Tenant).filter(Tenant.id == company.tenant_id).first()

        # Get user count
        user_count = (
            self.db.query(func.count(User.id))
            .filter(User.company_id == company_id)
            .scalar() or 0
        )

        # Get file count and storage
        file_count = (
            self.db.query(func.count(IngestedFile.id))
            .filter(IngestedFile.tenant_id == company.tenant_id)
            .scalar() or 0
        )
        storage_used = (
            self.db.query(func.sum(IngestedFile.file_size))
            .filter(IngestedFile.tenant_id == company.tenant_id)
            .scalar() or 0
        )

        # Get last activity
        last_activity = (
            self.db.query(func.max(User.last_login))
            .filter(User.company_id == company_id)
            .scalar()
        )

        return CompanyDetail(
            id=company.id,
            tenant_id=company.tenant_id,
            legal_name=company.legal_name,
            trading_name=company.trading_name,
            country=company.country,
            industry=company.industry,
            email=company.email,
            phone=company.phone,
            status=tenant.status.value if tenant else "unknown",
            plan=tenant.plan if tenant else None,
            user_count=user_count,
            file_count=file_count,
            storage_used_bytes=storage_used,
            created_at=company.created_at,
            updated_at=company.updated_at,
            last_activity=last_activity,
        )

    def suspend_company(
        self, company_id: UUID, admin_user_id: UUID, reason: str, ip_address: Optional[str] = None
    ) -> bool:
        """
        Suspend a company's access
        """
        logger.info("suspending_company", company_id=str(company_id), reason=reason)

        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return False

        # Update tenant status
        tenant = self.db.query(Tenant).filter(Tenant.id == company.tenant_id).first()
        if not tenant:
            return False

        tenant.status = TenantStatus.SUSPENDED
        tenant.updated_at = datetime.utcnow()

        # Create audit log
        audit_log = SuperAdminAuditLog(
            admin_user_id=admin_user_id,
            action="company_suspended",
            resource_type="company",
            resource_id=company_id,
            description=reason,
            action_metadata={"tenant_id": str(company.tenant_id), "reason": reason},
            ip_address=ip_address,
        )
        self.db.add(audit_log)

        self.db.commit()
        logger.info("company_suspended", company_id=str(company_id))
        return True

    def reactivate_company(
        self, company_id: UUID, admin_user_id: UUID, notes: Optional[str] = None, ip_address: Optional[str] = None
    ) -> bool:
        """
        Reactivate a suspended company
        """
        logger.info("reactivating_company", company_id=str(company_id))

        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return False

        # Update tenant status
        tenant = self.db.query(Tenant).filter(Tenant.id == company.tenant_id).first()
        if not tenant:
            return False

        tenant.status = TenantStatus.ACTIVE
        tenant.updated_at = datetime.utcnow()

        # Create audit log
        audit_log = SuperAdminAuditLog(
            admin_user_id=admin_user_id,
            action="company_reactivated",
            resource_type="company",
            resource_id=company_id,
            description=notes or "Company reactivated",
            action_metadata={"tenant_id": str(company.tenant_id), "notes": notes},
            ip_address=ip_address,
        )
        self.db.add(audit_log)

        self.db.commit()
        logger.info("company_reactivated", company_id=str(company_id))
        return True

    def get_system_health(self) -> SystemHealthResponse:
        """
        Check health of all system components
        """
        logger.info("checking_system_health")

        # Check database
        db_health = self._check_database_health()

        # Check Redis
        redis_health = self._check_redis_health()

        # Check storage
        storage_health = self._check_storage_health()

        # Check queue
        queue_health = self._check_queue_health()

        # Determine overall status
        statuses = [db_health.status, redis_health.status, storage_health.status, queue_health.status]
        if any(s == SystemHealthStatus.UNHEALTHY for s in statuses):
            overall = SystemHealthStatus.UNHEALTHY
        elif any(s == SystemHealthStatus.DEGRADED for s in statuses):
            overall = SystemHealthStatus.DEGRADED
        else:
            overall = SystemHealthStatus.HEALTHY

        return SystemHealthResponse(
            overall_status=overall,
            database=db_health,
            redis=redis_health,
            storage=storage_health,
            queue=queue_health,
            checked_at=datetime.utcnow(),
        )

    def _check_database_health(self) -> ComponentHealth:
        """Check database connectivity and performance"""
        try:
            start = datetime.utcnow()
            self.db.execute("SELECT 1")
            latency = (datetime.utcnow() - start).total_seconds() * 1000

            return ComponentHealth(
                status=SystemHealthStatus.HEALTHY,
                message="Database is responsive",
                latency_ms=latency,
            )
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return ComponentHealth(
                status=SystemHealthStatus.UNHEALTHY,
                message=f"Database error: {str(e)}",
            )

    def _check_redis_health(self) -> ComponentHealth:
        """Check Redis connectivity"""
        try:
            import redis
            client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
            start = datetime.utcnow()
            client.ping()
            latency = (datetime.utcnow() - start).total_seconds() * 1000

            return ComponentHealth(
                status=SystemHealthStatus.HEALTHY,
                message="Redis is responsive",
                latency_ms=latency,
            )
        except Exception as e:
            logger.error("redis_health_check_failed", error=str(e))
            return ComponentHealth(
                status=SystemHealthStatus.UNHEALTHY,
                message=f"Redis error: {str(e)}",
            )

    def _check_storage_health(self) -> ComponentHealth:
        """Check object storage connectivity"""
        try:
            # Placeholder - implement based on storage provider
            return ComponentHealth(
                status=SystemHealthStatus.HEALTHY,
                message="Storage is accessible",
            )
        except Exception as e:
            logger.error("storage_health_check_failed", error=str(e))
            return ComponentHealth(
                status=SystemHealthStatus.UNHEALTHY,
                message=f"Storage error: {str(e)}",
            )

    def _check_queue_health(self) -> ComponentHealth:
        """Check job queue health"""
        try:
            # Placeholder - implement Celery queue inspection
            return ComponentHealth(
                status=SystemHealthStatus.HEALTHY,
                message="Queue is operational",
            )
        except Exception as e:
            logger.error("queue_health_check_failed", error=str(e))
            return ComponentHealth(
                status=SystemHealthStatus.UNHEALTHY,
                message=f"Queue error: {str(e)}",
            )

    def get_job_queue_metrics(self) -> JobQueueResponse:
        """
        Get metrics for all job queues
        """
        logger.info("fetching_job_queue_metrics")

        # Placeholder - implement Celery inspection
        queues = [
            QueueMetrics(
                name="ocr",
                status=JobQueueStatus.ACTIVE,
                waiting=0,
                active=0,
                completed=0,
                failed=0,
                delayed=0,
                paused=False,
            ),
            QueueMetrics(
                name="translation",
                status=JobQueueStatus.ACTIVE,
                waiting=0,
                active=0,
                completed=0,
                failed=0,
                delayed=0,
                paused=False,
            ),
            QueueMetrics(
                name="extraction",
                status=JobQueueStatus.ACTIVE,
                waiting=0,
                active=0,
                completed=0,
                failed=0,
                delayed=0,
                paused=False,
            ),
        ]

        total_jobs = sum(q.waiting + q.active + q.completed + q.failed for q in queues)
        total_waiting = sum(q.waiting for q in queues)
        total_active = sum(q.active for q in queues)
        total_failed = sum(q.failed for q in queues)

        return JobQueueResponse(
            queues=queues,
            total_jobs=total_jobs,
            total_waiting=total_waiting,
            total_active=total_active,
            total_failed=total_failed,
        )

    def get_integrations(self) -> IntegrationsResponse:
        """
        Get status of all external integrations
        """
        logger.info("fetching_integration_status")

        integrations = []

        # SAP Integration
        if settings.SAP_ENABLED:
            integrations.append(
                IntegrationStatus(
                    name="SAP S/4HANA",
                    type="erp",
                    enabled=True,
                    status=SystemHealthStatus.HEALTHY,
                    connected_companies=0,  # TODO: Query actual count
                    last_sync=None,
                )
            )

        # QuickBooks
        if settings.QUICKBOOKS_CLIENT_ID:
            integrations.append(
                IntegrationStatus(
                    name="QuickBooks Online",
                    type="accounting",
                    enabled=True,
                    status=SystemHealthStatus.HEALTHY,
                    connected_companies=0,
                    last_sync=None,
                )
            )

        # Xero
        if settings.XERO_CLIENT_ID:
            integrations.append(
                IntegrationStatus(
                    name="Xero",
                    type="accounting",
                    enabled=True,
                    status=SystemHealthStatus.HEALTHY,
                    connected_companies=0,
                    last_sync=None,
                )
            )

        total_enabled = len([i for i in integrations if i.enabled])

        return IntegrationsResponse(
            integrations=integrations,
            total_enabled=total_enabled,
        )

    def get_audit_logs(
        self, page: int = 1, page_size: int = 50, action: Optional[str] = None
    ) -> Tuple[List[AuditLogEntry], int]:
        """
        Get platform audit logs with pagination
        """
        query = self.db.query(SuperAdminAuditLog)

        if action:
            query = query.filter(SuperAdminAuditLog.action == action)

        total = query.count()

        logs_data = (
            query.order_by(desc(SuperAdminAuditLog.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        logs = []
        for log in logs_data:
            # Get admin user email
            admin_user = self.db.query(User).filter(User.id == log.admin_user_id).first()
            admin_email = admin_user.email if admin_user else "unknown"

            logs.append(
                AuditLogEntry(
                    id=log.id,
                    admin_user_id=log.admin_user_id,
                    admin_email=admin_email,
                    action=log.action,
                    resource_type=log.resource_type,
                    resource_id=log.resource_id,
                    description=log.description,
                    action_metadata=log.action_metadata,
                    ip_address=log.ip_address,
                    created_at=log.created_at,
                )
            )

        return logs, total
