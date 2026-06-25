"""
Azure Blob Storage Adapter
Microsoft Azure Blob Storage implementation
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import structlog

from app.modules.storage.adapters.base import BaseStorage, StorageConfig

logger = structlog.get_logger(__name__)


class AzureBlobStorage(BaseStorage):
    """
    Azure Blob Storage implementation
    """

    def __init__(self, config: StorageConfig):
        """
        Initialize Azure Blob storage adapter

        Args:
            config: Storage configuration with Azure credentials
        """
        super().__init__(config)
        self._blob_service_client = None

    def _get_client(self):
        """
        Get or create Azure BlobServiceClient
        Lazy initialization
        """
        if self._blob_service_client is None:
            try:
                from azure.storage.blob import BlobServiceClient

                if self.config.connection_string:
                    self._blob_service_client = BlobServiceClient.from_connection_string(
                        self.config.connection_string
                    )
                else:
                    raise ValueError("Azure connection_string is required")

            except ImportError:
                raise ImportError(
                    "azure-storage-blob package required for Azure storage. "
                    "Install with: pip install azure-storage-blob"
                )

        return self._blob_service_client

    async def upload_file(
        self,
        file_content: bytes,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Upload file to Azure Blob Storage
        """
        logger.info("uploading_to_azure", container=self.config.bucket_name, blob=object_key)

        try:
            client = self._get_client()
            blob_client = client.get_blob_client(
                container=self.config.bucket_name,
                blob=object_key,
            )

            blob_client.upload_blob(
                file_content,
                overwrite=True,
                content_settings={
                    "content_type": content_type,
                } if content_type else None,
                metadata=metadata,
            )

            logger.info("azure_upload_successful", blob=object_key)
            return object_key

        except Exception as e:
            logger.error("azure_upload_failed", error=str(e), blob=object_key)
            raise

    async def download_file(self, object_key: str) -> bytes:
        """
        Download file from Azure Blob Storage
        """
        logger.info("downloading_from_azure", container=self.config.bucket_name, blob=object_key)

        try:
            client = self._get_client()
            blob_client = client.get_blob_client(
                container=self.config.bucket_name,
                blob=object_key,
            )

            download_stream = blob_client.download_blob()
            content = download_stream.readall()

            logger.info("azure_download_successful", blob=object_key, size=len(content))
            return content

        except Exception as e:
            logger.error("azure_download_failed", error=str(e), blob=object_key)
            raise

    async def delete_file(self, object_key: str) -> bool:
        """
        Delete file from Azure Blob Storage
        """
        logger.info("deleting_from_azure", container=self.config.bucket_name, blob=object_key)

        try:
            client = self._get_client()
            blob_client = client.get_blob_client(
                container=self.config.bucket_name,
                blob=object_key,
            )

            blob_client.delete_blob()

            logger.info("azure_delete_successful", blob=object_key)
            return True

        except Exception as e:
            logger.error("azure_delete_failed", error=str(e), blob=object_key)
            return False

    async def file_exists(self, object_key: str) -> bool:
        """
        Check if file exists in Azure Blob Storage
        """
        try:
            client = self._get_client()
            blob_client = client.get_blob_client(
                container=self.config.bucket_name,
                blob=object_key,
            )
            return blob_client.exists()
        except:
            return False

    async def get_file_metadata(self, object_key: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata from Azure Blob Storage
        """
        try:
            client = self._get_client()
            blob_client = client.get_blob_client(
                container=self.config.bucket_name,
                blob=object_key,
            )

            properties = blob_client.get_blob_properties()

            return {
                "size": properties.size,
                "content_type": properties.content_settings.content_type,
                "last_modified": properties.last_modified,
                "etag": properties.etag,
                "metadata": properties.metadata or {},
            }
        except Exception as e:
            logger.error("azure_get_metadata_failed", error=str(e), blob=object_key)
            return None

    async def generate_presigned_url(
        self,
        object_key: str,
        expiration: int = 3600,
        download: bool = False,
    ) -> str:
        """
        Generate SAS URL for Azure Blob
        """
        logger.info("generating_sas_url", blob=object_key, expiration=expiration)

        try:
            from azure.storage.blob import BlobSasPermissions, generate_blob_sas
            from datetime import datetime, timedelta

            client = self._get_client()
            blob_client = client.get_blob_client(
                container=self.config.bucket_name,
                blob=object_key,
            )

            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=blob_client.account_name,
                container_name=self.config.bucket_name,
                blob_name=object_key,
                account_key=client.credential.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(seconds=expiration),
            )

            # Build URL with SAS token
            url = f"{blob_client.url}?{sas_token}"

            logger.info("sas_url_generated", blob=object_key)
            return url

        except Exception as e:
            logger.error("sas_url_generation_failed", error=str(e), blob=object_key)
            raise

    async def copy_file(self, source_key: str, destination_key: str) -> bool:
        """
        Copy file within Azure Blob Storage
        """
        logger.info("copying_in_azure", source=source_key, destination=destination_key)

        try:
            client = self._get_client()

            source_blob = client.get_blob_client(
                container=self.config.bucket_name,
                blob=source_key,
            )

            destination_blob = client.get_blob_client(
                container=self.config.bucket_name,
                blob=destination_key,
            )

            # Start copy operation
            destination_blob.start_copy_from_url(source_blob.url)

            logger.info("azure_copy_successful", source=source_key, destination=destination_key)
            return True

        except Exception as e:
            logger.error("azure_copy_failed", error=str(e), source=source_key)
            return False
