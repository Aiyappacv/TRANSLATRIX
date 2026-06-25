"""
Monitoring Routes
API endpoints for monitoring and health checks
"""
from fastapi import APIRouter, Response

from app.modules.monitoring.service import MonitoringService
from app.modules.monitoring.schemas import HealthCheckResponse, SystemInfoResponse
from app.modules.monitoring.metrics import PrometheusMetrics

router = APIRouter()


@router.get("/health/detailed", response_model=HealthCheckResponse)
def detailed_health_check():
    """
    Detailed health check with all dependencies
    For monitoring systems
    """
    health_status = MonitoringService.get_health_status()
    return HealthCheckResponse(**health_status)


@router.get("/system-info", response_model=SystemInfoResponse)
def get_system_info():
    """Get system information"""
    system_info = MonitoringService.get_system_info()
    return SystemInfoResponse(**system_info)


@router.get("/metrics")
def get_prometheus_metrics():
    """
    Prometheus metrics endpoint
    Returns metrics in Prometheus text format
    """
    metrics = PrometheusMetrics.get_metrics()
    return Response(content=metrics, media_type="text/plain")
