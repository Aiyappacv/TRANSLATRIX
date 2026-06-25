"""
Monitoring Service
System monitoring and health checks
"""
from typing import Dict, Any
from datetime import datetime
import structlog

from app.modules.monitoring.health import HealthChecker

logger = structlog.get_logger(__name__)


class MonitoringService:
    """Service for system monitoring"""

    @staticmethod
    def get_health_status() -> Dict[str, Any]:
        """Get comprehensive health status"""
        health_checks = HealthChecker.check_all()

        return {
            "status": health_checks["overall_status"],
            "timestamp": datetime.utcnow().isoformat(),
            "checks": health_checks["checks"]
        }

    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Get system information"""
        import sys
        import platform

        return {
            "python_version": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "timestamp": datetime.utcnow().isoformat()
        }
