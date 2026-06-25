from __future__ import annotations

import asyncio
import structlog

from app.config import settings
from app.modules.storage.adapters.base import BaseStorage, StorageConfig
from app.modules.storage.adapters.minio import MinIOStorage
from app.modules.storage.adapters.s3 import S3Storage
from app.modules.storage.adapters.local import LocalStorage

logger = structlog.get_logger(__name__)


async def _tcp_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return True if a TCP connection to host:port succeeds within timeout."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception:
        return False


async def get_storage_adapter() -> BaseStorage:
    provider = settings.STORAGE_PROVIDER or "local"

    def _local_fallback():
        logger.warning("storage_adapter_fallback_local", provider=provider)
        config = StorageConfig(provider="local", bucket_name=settings.LOCAL_STORAGE_DIR or "storage_data")
        return LocalStorage(config)

    try:
        if provider == "local":
            logger.info("using_local_storage")
            config = StorageConfig(
                provider="local",
                bucket_name=settings.LOCAL_STORAGE_DIR or "storage_data",
            )
            return LocalStorage(config)

        if provider == "s3":
            logger.info("using_s3_storage")
            config = StorageConfig(
                provider="s3",
                bucket_name=settings.S3_BUCKET_NAME or "translatrix-files",
                access_key=settings.AWS_ACCESS_KEY_ID or settings.MINIO_ACCESS_KEY,
                secret_key=settings.AWS_SECRET_ACCESS_KEY or settings.MINIO_SECRET_KEY,
                region=settings.AWS_REGION or "us-east-1",
                endpoint_url=settings.MINIO_ENDPOINT,
            )
            return S3Storage(config)

        # MinIO path — probe TCP connectivity before returning the adapter.
        # MinIOStorage uses lazy client init so the constructor never throws;
        # without this probe a misconfigured/offline MinIO causes silent
        # per-file failures deep inside the upload pipeline.
        endpoint_url = settings.MINIO_ENDPOINT
        if endpoint_url and not endpoint_url.startswith("http"):
            protocol = "https" if settings.MINIO_SECURE else "http"
            endpoint_url = f"{protocol}://{endpoint_url}"

        raw_endpoint = settings.MINIO_ENDPOINT or "localhost:9000"
        host_port = raw_endpoint.replace("http://", "").replace("https://", "").split(":")
        minio_host = host_port[0]
        minio_port = int(host_port[1]) if len(host_port) > 1 else 9000

        reachable = await _tcp_reachable(minio_host, minio_port)
        if not reachable:
            logger.warning(
                "minio_unreachable_falling_back_to_local",
                host=minio_host,
                port=minio_port,
            )
            return _local_fallback()

        logger.info("using_minio_storage", endpoint_url=endpoint_url, bucket=settings.MINIO_BUCKET)

        config = StorageConfig(
            provider="minio",
            bucket_name=settings.MINIO_BUCKET or "translatrix-pro",
            endpoint_url=endpoint_url or "http://localhost:9000",
            access_key=settings.MINIO_ACCESS_KEY or "minioadmin",
            secret_key=settings.MINIO_SECRET_KEY or "minioadmin",
            region=settings.AWS_REGION,
        )
        return MinIOStorage(config)
    except Exception as exc:
        logger.warning("storage_adapter_init_exception", error=str(exc), provider=provider)
        try:
            return _local_fallback()
        except Exception:
            raise
