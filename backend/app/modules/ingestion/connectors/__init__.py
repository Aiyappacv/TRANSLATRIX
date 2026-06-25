"""
Connector Package
Abstraction layer for different file sources
"""
from app.modules.ingestion.connectors.base import BaseConnector, FileMetadata
from app.modules.ingestion.connectors.google_drive import GoogleDriveConnector
from app.modules.ingestion.connectors.onedrive import OneDriveConnector
from app.modules.ingestion.connectors.s3 import S3Connector
from app.modules.ingestion.connectors.local import LocalUploadConnector

__all__ = [
    "BaseConnector",
    "FileMetadata",
    "GoogleDriveConnector",
    "OneDriveConnector",
    "S3Connector",
    "LocalUploadConnector",
]
