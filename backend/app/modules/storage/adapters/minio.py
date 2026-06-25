"""
MinIO Storage Adapter
MinIO S3-compatible object storage implementation
"""
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import timedelta
import structlog

from app.modules.storage.adapters.base import BaseStorage, StorageConfig

logger = structlog.get_logger(__name__)


class MinIOStorage(BaseStorage):
    """
    MinIO storage implementation
    Uses S3-compatible API
    """

    def __init__(self, config: StorageConfig):
        """
        Initialize MinIO storage adapter

        Args:
            config: Storage configuration with MinIO credentials
        """
        super().__init__(config)
        self._client = None
        logger.info("minio_adapter_init",
                   endpoint_url=config.endpoint_url,
                   bucket=config.bucket_name,
                   has_access_key=bool(config.access_key))

    def _get_client(self):
        """
        Get or create MinIO client
        Lazy initialization
        """
        if self._client is None:
            try:
                import sys
                logger.info("attempting_minio_import",
                           python_version=sys.version,
                           python_executable=sys.executable,
                           sys_path_count=len(sys.path))

                # Log first 5 sys.path entries for debugging
                for i, path in enumerate(sys.path[:5]):
                    logger.info(f"sys_path_{i}", path=path)

                logger.info("importing_minio_now")
                from minio import Minio
                logger.info("minio_import_successful")

                # Parse endpoint URL
                endpoint = self.config.endpoint_url
                logger.info("parsing_endpoint",
                           raw_endpoint=endpoint,
                           provider=self.config.provider,
                           bucket=self.config.bucket_name)

                if endpoint:
                    # Remove http:// or https://
                    endpoint = endpoint.replace("http://", "").replace("https://", "")
                    secure = self.config.endpoint_url.startswith("https://")
                else:
                    logger.error("endpoint_missing", endpoint=endpoint)
                    raise ValueError("endpoint_url is required for MinIO")

                logger.info("creating_minio_client",
                           endpoint=endpoint,
                           secure=secure,
                           has_access_key=bool(self.config.access_key))

                # The minio SDK's default HTTP pool retries connection failures
                # with backoff (~4 attempts), which can take well over a minute
                # per call. With a fixed-size background worker pool, a handful
                # of uploads hitting an unreachable MinIO can occupy every
                # worker slot and silently stall all other uploads behind them
                # indefinitely. Fail fast instead so a dead storage backend
                # surfaces as a clear per-file error within seconds.
                import urllib3
                http_client = urllib3.PoolManager(
                    timeout=urllib3.Timeout(connect=3, read=10),
                    retries=urllib3.Retry(total=1, backoff_factor=0.2),
                )

                self._client = Minio(
                    endpoint,
                    access_key=self.config.access_key,
                    secret_key=self.config.secret_key,
                    secure=secure,
                    http_client=http_client,
                )

                # Ensure bucket exists
                logger.info("checking_bucket_exists", bucket=self.config.bucket_name)
                if not self._client.bucket_exists(self.config.bucket_name):
                    logger.info("creating_bucket", bucket=self.config.bucket_name)
                    self._client.make_bucket(self.config.bucket_name)

                logger.info("minio_client_ready")

            except ImportError as e:
                import traceback
                logger.error("minio_import_failed",
                            error=str(e),
                            error_type=type(e).__name__,
                            traceback=traceback.format_exc())
                raise ImportError("minio package required for MinIO storage. Install with: pip install minio")
            except Exception as e:
                import traceback
                logger.error("minio_client_creation_failed",
                            error=str(e),
                            error_type=type(e).__name__,
                            traceback=traceback.format_exc())
                raise

        return self._client

    async def upload_file(
        self,
        file_content: bytes,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Upload file to MinIO
        """
        logger.info("uploading_to_minio", bucket=self.config.bucket_name, key=object_key)

        try:
            from io import BytesIO

            client = self._get_client()

            file_stream = BytesIO(file_content)
            file_size = len(file_content)

            client.put_object(
                bucket_name=self.config.bucket_name,
                object_name=object_key,
                data=file_stream,
                length=file_size,
                content_type=content_type or "application/octet-stream",
                metadata=metadata,
            )

            logger.info("minio_upload_successful", key=object_key)
            return object_key

        except Exception as e:
            logger.error("minio_upload_failed", error=str(e), key=object_key)
            raise

    async def upload_stream(
        self,
        file_path: Path,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Upload a file already on local disk to MinIO via fput_object, which
        streams from disk in the SDK's own internal chunks rather than
        requiring the whole file in memory — the right primitive for large
        (multi-hundred-MB) documents.
        """
        logger.info("uploading_to_minio_streamed", bucket=self.config.bucket_name, key=object_key)
        try:
            client = self._get_client()
            # minio-py's fput_object is synchronous/blocking I/O — run it off
            # the event loop so it doesn't stall other concurrent uploads.
            await asyncio.to_thread(
                client.fput_object,
                bucket_name=self.config.bucket_name,
                object_name=object_key,
                file_path=str(file_path),
                content_type=content_type or "application/octet-stream",
                metadata=metadata,
            )
            logger.info("minio_upload_streamed_successful", key=object_key)
            return object_key
        except Exception as e:
            logger.error("minio_upload_streamed_failed", error=str(e), key=object_key)
            raise

    async def download_file(self, object_key: str) -> bytes:
        """
        Download file from MinIO
        """
        logger.info("downloading_from_minio", bucket=self.config.bucket_name, key=object_key)

        try:
            client = self._get_client()

            response = client.get_object(
                bucket_name=self.config.bucket_name,
                object_name=object_key,
            )

            content = response.read()
            response.close()
            response.release_conn()

            logger.info("minio_download_successful", key=object_key, size=len(content))
            return content

        except Exception as e:
            logger.error("minio_download_failed", error=str(e), key=object_key)
            raise

    async def delete_file(self, object_key: str) -> bool:
        """
        Delete file from MinIO
        """
        logger.info("deleting_from_minio", bucket=self.config.bucket_name, key=object_key)

        try:
            client = self._get_client()

            client.remove_object(
                bucket_name=self.config.bucket_name,
                object_name=object_key,
            )

            logger.info("minio_delete_successful", key=object_key)
            return True

        except Exception as e:
            logger.error("minio_delete_failed", error=str(e), key=object_key)
            return False

    async def file_exists(self, object_key: str) -> bool:
        """
        Check if file exists in MinIO
        """
        try:
            client = self._get_client()
            client.stat_object(
                bucket_name=self.config.bucket_name,
                object_name=object_key,
            )
            return True
        except:
            return False

    async def get_file_metadata(self, object_key: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata from MinIO
        """
        try:
            client = self._get_client()

            stat = client.stat_object(
                bucket_name=self.config.bucket_name,
                object_name=object_key,
            )

            return {
                "size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "etag": stat.etag,
                "metadata": stat.metadata or {},
            }
        except Exception as e:
            logger.error("minio_get_metadata_failed", error=str(e), key=object_key)
            return None

    async def generate_presigned_url(
        self,
        object_key: str,
        expiration: int = 3600,
        download: bool = False,
    ) -> str:
        """
        Generate presigned URL for MinIO object
        """
        logger.info("generating_presigned_url", key=object_key, expiration=expiration)

        try:
            from datetime import timedelta

            client = self._get_client()

            url = client.presigned_get_object(
                bucket_name=self.config.bucket_name,
                object_name=object_key,
                expires=timedelta(seconds=expiration),
            )

            logger.info("presigned_url_generated", key=object_key)
            return url

        except Exception as e:
            logger.error("presigned_url_generation_failed", error=str(e), key=object_key)
            raise

    async def copy_file(self, source_key: str, destination_key: str) -> bool:
        """
        Copy file within MinIO bucket
        """
        logger.info("copying_in_minio", source=source_key, destination=destination_key)

        try:
            from minio.commonconfig import CopySource

            client = self._get_client()

            client.copy_object(
                bucket_name=self.config.bucket_name,
                object_name=destination_key,
                source=CopySource(self.config.bucket_name, source_key),
            )

            logger.info("minio_copy_successful", source=source_key, destination=destination_key)
            return True

        except Exception as e:
            logger.error("minio_copy_failed", error=str(e), source=source_key)
            return False
