"""
Base Connector
Abstract interface for file source connectors
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class FileMetadata(BaseModel):
    """File metadata from external source"""
    name: str
    path: str
    size: int
    mime_type: Optional[str] = None
    modified_at: Optional[datetime] = None
    source_id: str  # External ID from source system
    download_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseConnector(ABC):
    """
    Abstract base connector for file sources
    All connectors must implement these methods
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize connector with configuration

        Args:
            config: Connector-specific configuration
        """
        self.config = config

    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate that connection credentials are working

        Returns:
            True if connection is valid, False otherwise
        """
        pass

    @abstractmethod
    async def list_files(
        self,
        path: Optional[str] = None,
        recursive: bool = False,
        file_types: Optional[List[str]] = None,
    ) -> List[FileMetadata]:
        """
        List files from the source

        Args:
            path: Optional path/folder to list from
            recursive: Whether to list recursively
            file_types: Optional filter by file extensions

        Returns:
            List of file metadata
        """
        pass

    @abstractmethod
    async def download_file(self, file_metadata: FileMetadata) -> bytes:
        """
        Download file content

        Args:
            file_metadata: Metadata of file to download

        Returns:
            File content as bytes
        """
        pass

    @abstractmethod
    async def get_file_info(self, file_id: str) -> Optional[FileMetadata]:
        """
        Get metadata for a specific file

        Args:
            file_id: External file identifier

        Returns:
            File metadata or None if not found
        """
        pass

    def supports_incremental_sync(self) -> bool:
        """
        Whether this connector supports incremental synchronization

        Returns:
            True if incremental sync is supported
        """
        return False

    async def get_changes_since(self, last_sync: datetime) -> List[FileMetadata]:
        """
        Get files that changed since last sync (for incremental sync)

        Args:
            last_sync: Timestamp of last synchronization

        Returns:
            List of changed files
        """
        raise NotImplementedError("Incremental sync not supported by this connector")
