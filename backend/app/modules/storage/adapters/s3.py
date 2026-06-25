"""
AWS S3 Storage Adapter
Amazon S3 object storage implementation
"""
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import timedelta
import structlog

from app.modules.storage.adapters.base import BaseStorage, StorageConfig

logger = structlog.get_logger(__name__)


class S3Storage(BaseStorage):
    """
    AWS S3 storage implementation
    """

    def __init__(self, config: StorageConfig):
        """
        Initialize S3 storage adapter

        Args:
            config: Storage configuration with S3 credentials
        """
        super().__init__(config)
        self._client = None

    def _get_client(self):
        """
        Get or create boto3 S3 client
        Lazy initialization
        """
        if self._client is None:
            try:
                import boto3

                self._client = boto3.client(
                    "s3",
                    aws_access_key_id=self.config.access_key,
                    aws_secret_access_key=self.config.secret_key,
                    region_name=self.config.region,
                )
            except ImportError:
                raise ImportError("boto3 package required for S3 storage. Install with: pip install boto3")

        return self._client

    async def upload_file(
        self,
        file_content: bytes,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Upload file to S3
        """
        logger.info("uploading_to_s3", bucket=self.config.bucket_name, key=object_key)

        try:
            client = self._get_client()

            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            if metadata:
                extra_args["Metadata"] = metadata

            client.put_object(
                Bucket=self.config.bucket_name,
                Key=object_key,
                Body=file_content,
                **extra_args,
            )

            logger.info("s3_upload_successful", key=object_key)
            return object_key

        except Exception as e:
            logger.error("s3_upload_failed", error=str(e), key=object_key)
            raise

    async def upload_stream(
        self,
        file_path: Path,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Upload a file already on local disk to S3 via the boto3 transfer
        manager's upload_file, which streams from disk and automatically
        switches to multipart upload for large files — never buffers the
        whole file in memory.
        """
        logger.info("uploading_to_s3_streamed", bucket=self.config.bucket_name, key=object_key)
        try:
            client = self._get_client()
            extra_args: Dict[str, Any] = {}
            if content_type:
                extra_args["ContentType"] = content_type
            if metadata:
                extra_args["Metadata"] = metadata

            await asyncio.to_thread(
                client.upload_file,
                str(file_path),
                self.config.bucket_name,
                object_key,
                ExtraArgs=extra_args or None,
            )
            logger.info("s3_upload_streamed_successful", key=object_key)
            return object_key
        except Exception as e:
            logger.error("s3_upload_streamed_failed", error=str(e), key=object_key)
            raise

    async def download_file(self, object_key: str) -> bytes:
        """
        Download file from S3
        """
        logger.info("downloading_from_s3", bucket=self.config.bucket_name, key=object_key)

        try:
            client = self._get_client()
            response = client.get_object(Bucket=self.config.bucket_name, Key=object_key)
            content = response["Body"].read()

            logger.info("s3_download_successful", key=object_key, size=len(content))
            return content

        except Exception as e:
            logger.error("s3_download_failed", error=str(e), key=object_key)
            raise

    async def delete_file(self, object_key: str) -> bool:
        """
        Delete file from S3
        """
        logger.info("deleting_from_s3", bucket=self.config.bucket_name, key=object_key)

        try:
            client = self._get_client()
            client.delete_object(Bucket=self.config.bucket_name, Key=object_key)

            logger.info("s3_delete_successful", key=object_key)
            return True

        except Exception as e:
            logger.error("s3_delete_failed", error=str(e), key=object_key)
            return False

    async def file_exists(self, object_key: str) -> bool:
        """
        Check if file exists in S3
        """
        try:
            client = self._get_client()
            client.head_object(Bucket=self.config.bucket_name, Key=object_key)
            return True
        except:
            return False

    async def get_file_metadata(self, object_key: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata from S3
        """
        try:
            client = self._get_client()
            response = client.head_object(Bucket=self.config.bucket_name, Key=object_key)

            return {
                "size": response.get("ContentLength"),
                "content_type": response.get("ContentType"),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag"),
                "metadata": response.get("Metadata", {}),
            }
        except Exception as e:
            logger.error("s3_get_metadata_failed", error=str(e), key=object_key)
            return None

    async def generate_presigned_url(
        self,
        object_key: str,
        expiration: int = 3600,
        download: bool = False,
    ) -> str:
        """
        Generate presigned URL for S3 object
        """
        logger.info("generating_presigned_url", key=object_key, expiration=expiration)

        try:
            client = self._get_client()

            params = {
                "Bucket": self.config.bucket_name,
                "Key": object_key,
            }

            if download:
                params["ResponseContentDisposition"] = f'attachment; filename="{object_key.split("/")[-1]}"'

            url = client.generate_presigned_url(
                ClientMethod="get_object",
                Params=params,
                ExpiresIn=expiration,
            )

            logger.info("presigned_url_generated", key=object_key)
            return url

        except Exception as e:
            logger.error("presigned_url_generation_failed", error=str(e), key=object_key)
            raise

    async def copy_file(self, source_key: str, destination_key: str) -> bool:
        """
        Copy file within S3 bucket
        """
        logger.info("copying_in_s3", source=source_key, destination=destination_key)

        try:
            client = self._get_client()

            copy_source = {
                "Bucket": self.config.bucket_name,
                "Key": source_key,
            }

            client.copy_object(
                CopySource=copy_source,
                Bucket=self.config.bucket_name,
                Key=destination_key,
            )

            logger.info("s3_copy_successful", source=source_key, destination=destination_key)
            return True

        except Exception as e:
            logger.error("s3_copy_failed", error=str(e), source=source_key)
            return False
