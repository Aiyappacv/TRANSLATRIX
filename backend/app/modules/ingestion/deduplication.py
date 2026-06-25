from __future__ import annotations

import hashlib
import json
import os
import structlog
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

import numpy as np
from sqlalchemy.orm import Session

from app.config import settings
from app.modules.files.models import IngestedFile
from app.modules.ingestion.tiered_storage import DocumentEmbedding, TieredStorageManager

logger = structlog.get_logger(__name__)

EMBEDDING_CACHE_DIR = Path(getattr(settings, "FRONTEND_UPLOAD_DIR", "/app/data/uploads")) / ".embeddings"
EMBEDDING_DIM = 384

SIMILARITY_HIGH = 0.95
SIMILARITY_MEDIUM = 0.85
SIMILARITY_LOW = 0.75


class DeduplicationResult:
    def __init__(
        self,
        is_duplicate: bool,
        similarity_score: float,
        matches: list[dict[str, Any]],
        embedding_id: Optional[str] = None,
    ):
        self.is_duplicate = is_duplicate
        self.similarity_score = similarity_score
        self.matches = matches
        self.embedding_id = embedding_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "isDuplicate": self.is_duplicate,
            "similarityScore": round(self.similarity_score, 4),
            "matches": self.matches,
            "embeddingId": self.embedding_id,
        }


class DeduplicationEngine:
    def __init__(self, db: Session, storage_manager: TieredStorageManager):
        self.db = db
        self.storage = storage_manager
        self._model = None
        self._index = None
        self._model_loaded = False

    def _get_model(self):
        if not self._model_loaded:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
                self._model_loaded = True
            except ImportError:
                logger.warning("sentence_transformers not available; using fallback hash-based deduplication")
                self._model_loaded = True
        return self._model

    def _compute_embedding(self, text: str) -> list[float]:
        model = self._get_model()
        if model is None:
            return []
        try:
            embedding = model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as exc:
            logger.error("embedding_computation_failed", error=str(exc))
            return []

    def _build_document_text(self, file_record: IngestedFile, content_bytes: Optional[bytes] = None) -> str:
        parts: list[str] = [file_record.original_filename or ""]
        if content_bytes:
            raw = content_bytes.decode("utf-8", errors="replace")[:10000]
            parts.append(raw)
        return "\n".join(parts)

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        arr_a = np.array(a, dtype=np.float32)
        arr_b = np.array(b, dtype=np.float32)
        norm_a = np.linalg.norm(arr_a)
        norm_b = np.linalg.norm(arr_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(arr_a, arr_b) / (norm_a * norm_b))

    async def check_duplicate(
        self,
        file_id: UUID,
        tenant_id: UUID,
        company_id: UUID,
        filename: str,
        content_bytes: bytes,
    ) -> DeduplicationResult:
        text = self._build_document_text(
            IngestedFile(original_filename=filename),
            content_bytes,
        )
        embedding = self._compute_embedding(text)

        if not embedding:
            checksum = hashlib.sha256(content_bytes).hexdigest()
            existing = (
                self.db.query(IngestedFile)
                .filter(IngestedFile.checksum == checksum, IngestedFile.tenant_id == tenant_id)
                .first()
            )
            if existing:
                return DeduplicationResult(
                    is_duplicate=True,
                    similarity_score=1.0,
                    matches=[{"fileId": str(existing.id), "filename": existing.original_filename, "similarity": 1.0, "method": "exact_hash"}],
                )
            return DeduplicationResult(is_duplicate=False, similarity_score=0.0, matches=[])

        existing_embeddings = (
            self.db.query(DocumentEmbedding)
            .filter(DocumentEmbedding.tenant_id == tenant_id, DocumentEmbedding.embedding_dim == EMBEDDING_DIM)
            .all()
        )
        matches: list[dict[str, Any]] = []
        max_similarity = 0.0

        for existing in existing_embeddings:
            try:
                embedding_bytes = await self.storage.storage.download_file(existing.embedding_path)
                stored_embedding = json.loads(embedding_bytes.decode("utf-8"))
            except Exception:
                continue
            similarity = self._cosine_similarity(embedding, stored_embedding)
            if similarity > SIMILARITY_LOW:
                existing_file = self.db.query(IngestedFile).filter(IngestedFile.id == existing.file_id).first()
                matches.append({
                    "fileId": str(existing.file_id),
                    "filename": existing_file.original_filename if existing_file else "Unknown",
                    "similarity": round(similarity, 4),
                    "method": "semantic",
                })
            max_similarity = max(max_similarity, similarity)

        matches.sort(key=lambda m: m["similarity"], reverse=True)

        if embedding:
            embedding_path = f"embeddings/tenants/{tenant_id}/{file_id}.json"
            EMBEDDING_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            await self.storage.storage.upload_file(
                file_content=json.dumps(embedding).encode("utf-8"),
                object_key=embedding_path,
                content_type="application/json",
                metadata={"tenant_id": str(tenant_id), "file_id": str(file_id), "model": "all-MiniLM-L6-v2"},
            )
            embed_record = DocumentEmbedding(
                file_id=file_id,
                tenant_id=tenant_id,
                embedding_dim=EMBEDDING_DIM,
                embedding_path=embedding_path,
                model_name="all-MiniLM-L6-v2",
                checksum=hashlib.sha256(json.dumps(embedding).encode()).hexdigest(),
            )
            self.db.add(embed_record)
            self.db.commit()
            self.db.refresh(embed_record)
            embedding_id = str(embed_record.id)
        else:
            embedding_id = None

        return DeduplicationResult(
            is_duplicate=max_similarity >= SIMILARITY_HIGH,
            similarity_score=max_similarity,
            matches=matches[:5],
            embedding_id=embedding_id,
        )

    def get_similar_documents(
        self,
        file_id: UUID,
        tenant_id: UUID,
        min_similarity: float = SIMILARITY_LOW,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        current_embedding = (
            self.db.query(DocumentEmbedding)
            .filter(DocumentEmbedding.file_id == file_id, DocumentEmbedding.tenant_id == tenant_id)
            .first()
        )
        if not current_embedding:
            return []
        return self._search_similar(current_embedding, tenant_id, min_similarity, limit)

    def _search_similar(
        self,
        query_embedding: DocumentEmbedding,
        tenant_id: UUID,
        min_similarity: float,
        limit: int,
    ) -> list[dict[str, Any]]:
        all_embeddings = (
            self.db.query(DocumentEmbedding)
            .filter(
                DocumentEmbedding.tenant_id == tenant_id,
                DocumentEmbedding.id != query_embedding.id,
            )
            .all()
        )
        results: list[dict[str, Any]] = []
        for emb in all_embeddings:
            results.append({
                "fileId": str(emb.file_id),
                "modelName": emb.model_name,
                "createdAt": emb.created_at.isoformat() if emb.created_at else None,
                "similarity": 0.0,
            })
        return results[:limit]
