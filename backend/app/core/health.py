"""
Health Check Utilities
Check status of application dependencies
"""
from typing import Dict
import structlog
from sqlalchemy import text
from redis import Redis

from app.database import engine
from app.config import settings

logger = structlog.get_logger(__name__)


def check_database() -> str:
    """
    Check PostgreSQL database connection

    Returns:
        "healthy", "unhealthy", or "unknown"
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "healthy"
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return "unhealthy"


def check_redis() -> str:
    """
    Check Redis connection

    Returns:
        "healthy", "unhealthy", or "unknown"
    """
    try:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.ping()
        redis_client.close()
        return "healthy"
    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))
        return "unhealthy"


def check_storage() -> str:
    """
    Check storage (MinIO/S3) connection

    Returns:
        "healthy", "unhealthy", or "unknown"
    """
    try:
        if settings.MINIO_ENDPOINT:
            from minio import Minio

            logger.info(
                "checking_storage",
                endpoint=settings.MINIO_ENDPOINT,
                bucket=settings.MINIO_BUCKET,
                secure=settings.MINIO_SECURE
            )

            client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )

            # Check if bucket exists
            bucket_name = settings.MINIO_BUCKET or "translatrix-files"
            exists = client.bucket_exists(bucket_name)

            logger.info(
                "storage_check_result",
                bucket=bucket_name,
                exists=exists
            )

            return "healthy"
        else:
            # If storage not configured, return unknown
            logger.info("storage_not_configured")
            return "unknown"
    except Exception as e:
        logger.error(
            "storage_health_check_failed",
            error=str(e),
            error_type=type(e).__name__,
            endpoint=settings.MINIO_ENDPOINT
        )
        import traceback
        logger.error("storage_traceback", traceback=traceback.format_exc())
        return "unhealthy"


def check_all_dependencies() -> Dict[str, str]:
    """
    Check all application dependencies

    Returns:
        Dictionary with health status of each dependency
    """
    return {
        "database": check_database(),
        "redis": check_redis(),
        "storage": check_storage(),
    }


def is_system_ready() -> bool:
    """
    Determine if system is ready to handle requests

    Returns:
        True if all critical dependencies are healthy
    """
    deps = check_all_dependencies()

    # Database and Redis are critical
    critical_deps = ["database", "redis"]

    for dep in critical_deps:
        if deps.get(dep) != "healthy":
            return False

    return True
