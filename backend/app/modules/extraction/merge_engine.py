"""
Merge engine for chunked Gemini extraction results.

Each chunk is extracted independently against the same field schema. This
module combines those independent chunk outputs into one document-level
result: concatenating text/tables in page order, and for every field that
appears in more than one chunk, keeping the highest-confidence non-null
value (rather than silently overwriting with whichever chunk happened to
run last in the concurrent batch).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Fields that should be concatenated across chunks rather than
# conflict-resolved to a single winning value.
_LIST_FIELDS = {"line_items"}
# Nested dict fields where we merge key-by-key instead of picking one chunk's
# whole dict wholesale, so e.g. a packing_list_number found in chunk 1's
# additional_fields doesn't get discarded by chunk 3's additional_fields dict.
_DICT_MERGE_FIELDS = {"bank_details", "customs_declaration", "additional_fields"}


@dataclass
class ChunkExtractionResult:
    chunk_index: int
    start_page: int
    end_page: int
    total_chunks: int
    success: bool
    full_text: str = ""
    tables: list[dict[str, Any]] = field(default_factory=list)
    extracted_fields: dict[str, Any] = field(default_factory=dict)
    field_confidence: dict[str, float] = field(default_factory=dict)
    field_pages: dict[str, int] = field(default_factory=dict)
    document_type: str = "other"
    language: str = "en"
    confidence: float = 0.0
    word_count: int = 0
    error: str | None = None
    retries: int = 0


@dataclass
class MergedExtractionResult:
    full_text: str
    tables: list[dict[str, Any]]
    extracted_fields: dict[str, Any]
    field_confidence: dict[str, float]
    field_pages: dict[str, int]
    document_type: str
    language: str
    overall_confidence: float
    word_count: int
    page_count: int
    total_chunks: int
    chunks_succeeded: int
    failed_chunks: list[dict[str, Any]]


def _merge_scalar_field(
    key: str,
    existing_value: Any,
    existing_conf: float,
    candidate_value: Any,
    candidate_conf: float,
) -> tuple[Any, float, bool]:
    """Returns (winning_value, winning_confidence, candidate_won)."""
    if candidate_value is None or candidate_value == "":
        return existing_value, existing_conf, False
    if existing_value is None or existing_value == "":
        return candidate_value, candidate_conf, True
    if candidate_conf > existing_conf:
        return candidate_value, candidate_conf, True
    return existing_value, existing_conf, False


def _merge_dict_field(existing: dict[str, Any] | None, candidate: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(existing or {})
    for k, v in (candidate or {}).items():
        if v is None or v == "":
            continue
        if k not in merged or merged[k] in (None, ""):
            merged[k] = v
    return merged


def merge_chunk_results(
    chunks: list[ChunkExtractionResult],
    total_pages: int,
) -> MergedExtractionResult:
    ordered = sorted(chunks, key=lambda c: c.chunk_index)
    successful = [c for c in ordered if c.success]
    failed = [
        {"chunk_index": c.chunk_index, "pages": f"{c.start_page}-{c.end_page}", "error": c.error, "retries": c.retries}
        for c in ordered if not c.success
    ]

    if not successful:
        return MergedExtractionResult(
            full_text="", tables=[], extracted_fields={}, field_confidence={}, field_pages={},
            document_type="other", language="en", overall_confidence=0.0, word_count=0,
            page_count=total_pages, total_chunks=len(ordered), chunks_succeeded=0,
            failed_chunks=failed,
        )

    text_parts: list[str] = []
    all_tables: list[dict[str, Any]] = []
    merged_fields: dict[str, Any] = {}
    merged_confidence: dict[str, float] = {}
    merged_pages: dict[str, int] = {}
    line_items: list[Any] = []
    confidences: list[float] = []
    word_count_total = 0
    document_type_votes: dict[str, int] = {}
    language_votes: dict[str, int] = {}

    for chunk in successful:
        if chunk.full_text:
            text_parts.append(f"[Pages {chunk.start_page}-{chunk.end_page}]\n{chunk.full_text}")
        all_tables.extend(chunk.tables)
        confidences.append(chunk.confidence)
        word_count_total += chunk.word_count
        if chunk.document_type and chunk.document_type != "other":
            document_type_votes[chunk.document_type] = document_type_votes.get(chunk.document_type, 0) + 1
        if chunk.language and chunk.language != "unknown":
            language_votes[chunk.language] = language_votes.get(chunk.language, 0) + 1

        for fkey, fval in chunk.extracted_fields.items():
            if fkey in _LIST_FIELDS:
                if isinstance(fval, list):
                    line_items.extend(fval)
                continue
            if fkey in _DICT_MERGE_FIELDS:
                if isinstance(fval, dict):
                    merged_fields[fkey] = _merge_dict_field(merged_fields.get(fkey), fval)
                continue

            candidate_conf = float(chunk.field_confidence.get(fkey, chunk.confidence) or 0.0)
            existing_conf = float(merged_confidence.get(fkey, 0.0))
            winner, winner_conf, candidate_won = _merge_scalar_field(
                fkey, merged_fields.get(fkey), existing_conf, fval, candidate_conf,
            )
            merged_fields[fkey] = winner
            merged_confidence[fkey] = winner_conf
            if candidate_won:
                merged_pages[fkey] = chunk.field_pages.get(fkey, chunk.start_page)
            elif fkey not in merged_pages and winner is not None:
                merged_pages[fkey] = chunk.field_pages.get(fkey, chunk.start_page)

    if line_items:
        merged_fields["line_items"] = line_items

    document_type = max(document_type_votes, key=document_type_votes.get) if document_type_votes else (
        successful[0].document_type or "other"
    )
    language = max(language_votes, key=language_votes.get) if language_votes else (successful[0].language or "en")
    overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    if failed:
        # Penalise overall confidence proportionally to how much of the
        # document failed extraction, so a partially-failed large document
        # is visibly flagged rather than reported at full confidence.
        coverage = len(successful) / max(1, len(ordered))
        overall_confidence = round(overall_confidence * coverage, 4)

    logger.info(
        "extraction_merge_complete",
        total_pages=total_pages,
        total_chunks=len(ordered),
        chunks_succeeded=len(successful),
        chunks_failed=len(failed),
        fields_merged=len(merged_fields),
        document_type=document_type,
        overall_confidence=overall_confidence,
    )

    return MergedExtractionResult(
        full_text="\n\n".join(text_parts),
        tables=all_tables,
        extracted_fields=merged_fields,
        field_confidence=merged_confidence,
        field_pages=merged_pages,
        document_type=document_type,
        language=language,
        overall_confidence=overall_confidence,
        word_count=word_count_total,
        page_count=total_pages,
        total_chunks=len(ordered),
        chunks_succeeded=len(successful),
        failed_chunks=failed,
    )
