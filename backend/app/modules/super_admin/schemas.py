"""
Super Admin Schemas
Request/Response models for super admin operations
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, UUID4
from datetime import datetime
from enum import Enum


class SystemHealthStatus(str, Enum):
    """System component health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class JobQueueStatus(str, Enum):
    """Job queue status"""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"


# Dashboard Schemas
class PlatformStats(BaseModel):
    """Platform-wide statistics"""
    total_companies: int
    active_companies: int
    suspended_companies: int
    total_users: int
    active_users: int
    total_files_processed: int
    files_processed_today: int
    total_storage_used_bytes: int
    avg_processing_time_seconds: float


class RevenueMetrics(BaseModel):
    """Revenue and billing metrics"""
    monthly_recurring_revenue: float
    total_revenue: float
    average_revenue_per_user: float


class DashboardResponse(BaseModel):
    """Super admin dashboard data"""
    stats: PlatformStats
    revenue: Optional[RevenueMetrics] = None
    recent_signups: int
    system_health: str


# Company Management Schemas
class CompanyListItem(BaseModel):
    """Company list item for super admin"""
    id: UUID4
    tenant_id: UUID4
    legal_name: str
    trading_name: Optional[str]
    email: str
    country: str
    status: str
    user_count: int
    created_at: datetime
    last_activity: Optional[datetime]

    class Config:
        from_attributes = True


class CompanyDetail(BaseModel):
    """Detailed company information"""
    id: UUID4
    tenant_id: UUID4
    legal_name: str
    trading_name: Optional[str]
    country: str
    industry: Optional[str]
    email: str
    phone: Optional[str]
    status: str
    plan: Optional[str]
    user_count: int
    file_count: int
    storage_used_bytes: int
    created_at: datetime
    updated_at: datetime
    last_activity: Optional[datetime]

    class Config:
        from_attributes = True


class CompanyListResponse(BaseModel):
    """Paginated company list"""
    companies: List[CompanyListItem]
    total: int
    page: int
    page_size: int


class CompanySuspendRequest(BaseModel):
    """Request to suspend a company"""
    reason: str = Field(..., min_length=10, max_length=500)
    notify_users: bool = True


class CompanyReactivateRequest(BaseModel):
    """Request to reactivate a company"""
    notes: Optional[str] = Field(None, max_length=500)


# System Health Schemas
class ComponentHealth(BaseModel):
    """Individual system component health"""
    status: SystemHealthStatus
    message: Optional[str] = None
    latency_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class SystemHealthResponse(BaseModel):
    """System health check response"""
    overall_status: SystemHealthStatus
    database: ComponentHealth
    redis: ComponentHealth
    storage: ComponentHealth
    queue: ComponentHealth
    checked_at: datetime


# Job Queue Schemas
class QueueMetrics(BaseModel):
    """Metrics for a single queue"""
    name: str
    status: JobQueueStatus
    waiting: int
    active: int
    completed: int
    failed: int
    delayed: int
    paused: bool


class JobQueueResponse(BaseModel):
    """Job queue metrics response"""
    queues: List[QueueMetrics]
    total_jobs: int
    total_waiting: int
    total_active: int
    total_failed: int


# Integration Schemas
class IntegrationStatus(BaseModel):
    """Status of external integrations"""
    name: str
    type: str
    enabled: bool
    status: SystemHealthStatus
    connected_companies: int
    last_sync: Optional[datetime]
    error_message: Optional[str] = None


class IntegrationsResponse(BaseModel):
    """All platform integrations"""
    integrations: List[IntegrationStatus]
    total_enabled: int


# Audit Log Schemas
class AuditLogEntry(BaseModel):
    """Audit log entry"""
    id: UUID4
    admin_user_id: UUID4
    admin_email: str
    action: str
    resource_type: Optional[str]
    resource_id: Optional[UUID4]
    description: Optional[str]
    action_metadata: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Paginated audit log list"""
    logs: List[AuditLogEntry]
    total: int
    page: int
    page_size: int
