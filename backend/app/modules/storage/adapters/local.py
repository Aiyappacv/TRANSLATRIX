import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

from app.config import settings
from app.modules.storage.adapters.base import BaseStorage, StorageConfig

logger = structlog.get_logger(__name__)

STORAGE_DIR = Path(settings.LOCAL_STORAGE_DIR or "storage_data")


class LocalStorage(BaseStorage):
    def __init__(self, config: StorageConfig):
        super().__init__(config)
        self._base_path = STORAGE_DIR / config.bucket_name
        self._base_path.mkdir(parents=True, exist_ok=True)
        logger.info("local_storage_init", path=str(self._base_path))

    def _resolve(self, object_key: str) -> Path:
        safe = object_key.replace("\\", "/").lstrip("/")
        full = self._base_path / safe
        full.parent.mkdir(parents=True, exist_ok=True)
        return full

    async def upload_file(
        self,
        file_content: bytes,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        path = self._resolve(object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(file_content)
        logger.info("local_file_uploaded", object_key=object_key, size=len(file_content))
        return object_key

    async def upload_stream(
        self,
        file_path: Path,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        dest = self._resolve(object_key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Same filesystem: instant rename, no copy at all.
            os.replace(str(file_path), str(dest))
        except OSError:
            # Cross-device (e.g. temp dir on a different drive) — copy then
            # remove the source; shutil.copyfile streams in OS-buffered
            # chunks rather than reading the whole file into memory.
            shutil.copyfile(str(file_path), str(dest))
            Path(file_path).unlink(missing_ok=True)
        logger.info("local_file_uploaded_streamed", object_key=object_key, size=dest.stat().st_size)
        return object_key

    async def download_file(self, object_key: str) -> bytes:
        path = self._resolve(object_key)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {object_key}")
        return path.read_bytes()

    async def delete_file(self, object_key: str) -> bool:
        path = self._resolve(object_key)
        if not path.exists():
            logger.warning("local_file_not_found_for_delete", object_key=object_key)
            return False
        path.unlink()
        logger.info("local_file_deleted", object_key=object_key)
        return True

    async def file_exists(self, object_key: str) -> bool:
        return self._resolve(object_key).exists()

    async def get_file_metadata(self, object_key: str) -> Optional[Dict[str, Any]]:
        path = self._resolve(object_key)
        if not path.exists():
            return None
        stat = path.stat()
        return {
            "size": stat.st_size,
            "content_length": stat.st_size,
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        }

    async def generate_presigned_url(
        self,
        object_key: str,
        expiration: int = 3600,
        download: bool = False,
    ) -> str:
        path = self._resolve(object_key).resolve()
        return path.as_uri()

    async def copy_file(self, source_key: str, destination_key: str) -> bool:
        src = self._resolve(source_key)
        dst = self._resolve(destination_key)
        if not src.exists():
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        return True

    async def get_file_size(self, object_key: str) -> Optional[int]:
        path = self._resolve(object_key)
        if not path.exists():
            return None
        return path.stat().st_size
