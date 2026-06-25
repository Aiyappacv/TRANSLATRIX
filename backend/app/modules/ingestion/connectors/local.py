"""
Local Upload Connector
Handle direct file uploads (non-cloud source)
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import structlog

from app.modules.ingestion.connectors.base import BaseConnector, FileMetadata

logger = structlog.get_logger(__name__)


class LocalUploadConnector(BaseConnector):
    """
    Local upload connector
    Handles files uploaded directly through the API
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize local upload connector

        Args:
            config: Configuration (not used for local uploads)
        """
        super().__init__(config)

    async def validate_connection(self) -> bool:
        """
        Local uploads always valid
        """
        return True

    async def list_files(
        self,
        path: Optional[str] = None,
        recursive: bool = False,
        file_types: Optional[List[str]] = None,
    ) -> List[FileMetadata]:
        """
        Not applicable for local uploads
        Files are provided directly via upload
        """
        logger.warning("list_files_not_supported_for_local_uploads")
        return []

    async def download_file(self, file_metadata: FileMetadata) -> bytes:
        """
        Not applicable for local uploads
        File content is provided directly
        """
        logger.warning("download_not_supported_for_local_uploads")
        raise NotImplementedError("Download not supported for local uploads")

    async def get_file_info(self, file_id: str) -> Optional[FileMetadata]:
        """
        Not applicable for local uploads
        """
        logger.warning("get_file_info_not_supported_for_local_uploads")
        return None

    def supports_incremental_sync(self) -> bool:
        """Local uploads don't support sync"""
        return False
