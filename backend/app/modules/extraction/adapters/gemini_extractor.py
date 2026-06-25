"""
Gemini 2.5 Pro Extraction Adapter
Uses Gemini 2.5 Pro for document extraction including OCR understanding,
layout analysis, table extraction, key-value pair extraction, entity extraction,
document classification, and structured JSON generation.

For PDFs, Gemini acts as BOTH the OCR engine and the structured-field
extractor — there is no secondary OCR pass. Multi-page PDFs are never sent
as a single request (see `extract_chunk` / app.modules.extraction.chunking);
each page-range chunk is its own independent request, which keeps every
call well within Gemini's output token budget regardless of total document
length.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
import importlib.util
import io
import json
import base64
import httpx
import structlog

from .base import BaseExtractor, ExtractionResult, ExtractionError
from app.modules.extraction.merge_engine import ChunkExtractionResult
from app.modules.extraction.schema_registry import schema_guidance_for, normalize_document_type

logger = structlog.get_logger(__name__)


class GeminiExtractor(BaseExtractor):
    """
    Gemini 2.5 Pro based document extractor.
    Handles OCR understanding, layout analysis, table extraction,
    key-value pair extraction, entity extraction, document classification,
    and structured JSON generation for multi-page documents.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_key = self.config.get("api_key")
        self.model = self.config.get("model", "gemini-2.5-pro")
        self.classify_model = self.config.get("classify_model", "gemini-2.5-flash-lite")
        self.supported_mimes = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "text/csv",
            "image/png",
            "image/jpeg",
            "image/tiff",
            "image/bmp",
            "text/plain",
            "application/json",
            "text/xml",
            "application/xml",
        ]

    @staticmethod
    def _clean_json_response(raw: str) -> str:
        """Remove markdown code fences and leading/trailing whitespace from a
        Gemini response that should be pure JSON. Handles ```json, ```, and
        mixed formatting robustly."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            # Strip opening fence (```json or ```)
            first_newline = cleaned.find("\n")
            if first_newline != -1:
                cleaned = cleaned[first_newline + 1:]
            # Strip closing fence
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
        return cleaned.strip()

    def _client_available(self) -> bool:
        """Return True when the Gemini client can be used."""
        if not self.api_key:
            return False
        try:
            return importlib.util.find_spec("google.genai") is not None
        except Exception:
            return False

    def can_extract(self, file_path: Path, mime_type: str) -> bool:
        return mime_type in self.supported_mimes and self._client_available()

    def extract(
        self,
        file_path: Path,
        extract_tables: bool = True,
        extract_metadata: bool = True,
        document_type: Optional[str] = None,
        **kwargs
    ) -> ExtractionResult:
        if not self.api_key:
            raise ExtractionError(
                "GEMINI_API_KEY is not configured. Set it in the environment to enable Gemini extraction."
            )

        try:
            import google.genai as genai
        except ImportError:
            raise ExtractionError("Gemini library not installed: pip install google-genai")

        raw: str | None = None
        try:
            client = genai.Client(api_key=self.api_key)

            file_suffix = file_path.suffix.lower()

            prompt = self._build_extraction_prompt(extract_tables, extract_metadata, document_type=document_type)

            contents = self._build_contents(client, prompt, file_path, file_suffix)

            response = client.models.generate_content(
                model=self.model,
                contents=contents,
                config={
                    "temperature": 0.0,
                    "response_mime_type": "application/json",
                },
            )

            raw = self._clean_json_response(response.text)
            parsed = json.loads(raw)

            full_text = parsed.get("full_text", "")
            tables = parsed.get("tables", [])
            metadata = parsed.get("metadata", {})
            extracted_fields = parsed.get("extracted_fields", {})
            field_confidence = parsed.get("field_confidence", {})
            page_count = parsed.get("page_count", 1)
            confidence = parsed.get("confidence", 0.92)
            word_count = parsed.get("word_count", len(full_text.split()))
            document_type = parsed.get("document_type", "unknown")
            language = parsed.get("language", "unknown")

            combined_metadata = {
                "document_type": document_type,
                "language": language,
                "extracted_fields": extracted_fields,
                "field_confidence": field_confidence,
                "model": self.model,
                "provider": "gemini",
            }
            if extract_metadata:
                combined_metadata.update(metadata)

            logger.info(
                "gemini_extraction_complete",
                pages=page_count,
                text_length=len(full_text),
                tables=len(tables),
                document_type=document_type,
                confidence=confidence,
            )

            return ExtractionResult(
                text=full_text,
                tables=tables,
                metadata=combined_metadata,
                page_count=page_count,
                word_count=word_count,
                confidence=confidence,
            )

        except json.JSONDecodeError as e:
            logger.error("gemini_extraction_json_parse_error", error=str(e), raw_response=raw)
            raise ExtractionError(f"Gemini returned invalid JSON: {str(e)}")
        except genai.errors.APIError as e:
            logger.error("gemini_extraction_api_error", code=getattr(e, "code", None), error=str(e), file_path=str(file_path))
            code = getattr(e, "code", None)
            msg_lower = str(e).lower()
            if code == 401 or code == 403:
                raise ExtractionError("Gemini API authentication failed: invalid or unauthorized API key.")
            if code == 429:
                is_billing = "prepayment" in msg_lower or "credits are depleted" in msg_lower or "manage your project and billing" in msg_lower
                if is_billing:
                    raise ExtractionError("Gemini API quota exhausted. Your prepayment credits are depleted — please top up your Google AI Studio balance to continue.")
                raise ExtractionError("Gemini API rate limit reached. Please wait a moment and try again.")
            if code and code >= 500:
                raise ExtractionError(f"Gemini API service error ({code}). Please retry later.")
            raise ExtractionError(f"Gemini extraction failed: {str(e)}")
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            logger.error("gemini_extraction_network_error", error=str(e), file_path=str(file_path))
            raise ExtractionError(f"Network error contacting Gemini API: {str(e)}")
        except Exception as e:
            logger.error("gemini_extraction_error", error=str(e), file_path=str(file_path))
            raise ExtractionError(f"Gemini extraction failed: {str(e)}")

    def _build_contents(self, client: Any, prompt: str, file_path: Path, file_suffix: str) -> List[Any]:
        import google.genai as genai

        file_bytes = file_path.read_bytes()

        # Images: inline base64 data with correct MIME type
        image_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
        if file_suffix in image_extensions:
            encoded = base64.b64encode(file_bytes).decode("utf-8")
            mime_map = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".tiff": "image/tiff",
                ".bmp": "image/bmp",
            }
            part = genai.types.Part.from_bytes(
                data=encoded,
                mime_type=mime_map.get(file_suffix, "image/png"),
            )
            return [prompt, part]

        # PDF / DOCX / XLSX: upload via File API so Gemini reads the binary correctly
        doc_mime_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".csv": "text/csv",
        }
        if file_suffix in doc_mime_map:
            uploaded = client.files.upload(
                file=file_path,
                config={"mime_type": doc_mime_map[file_suffix]},
            )
            part = genai.types.Part.from_uri(
                file_uri=uploaded.uri,
                mime_type=doc_mime_map[file_suffix],
            )
            return [prompt, part]

        # Plain text / code: send as inline text
        text_content = file_bytes.decode("utf-8", errors="replace")
        return [prompt, text_content[:100000]]

    # ── Multi-page chunked extraction ───────────────────────────────
    # Gemini is the only OCR/extraction engine in this pipeline. For PDFs
    # with more than one chunk's worth of pages, the document is split into
    # independent page-range chunks (see app.modules.extraction.chunking)
    # and each chunk is sent here separately, rather than uploading the
    # entire PDF in one request and hoping the response covers every page.

    def classify_document(self, first_chunk_pdf_bytes: bytes) -> str:
        """Cheap, page-1-only classification call used to pick which schema
        guidance the real chunk extraction calls should focus on. Uses a
        faster/cheaper model (flash-lite) since this only needs a single label.
        Falls back to "other" on any failure rather than blocking extraction."""
        if not self.api_key:
            return "other"
        try:
            import google.genai as genai
        except ImportError:
            return "other"

        try:
            client = genai.Client(api_key=self.api_key)
            prompt = (
                "Classify this document. Return ONLY valid JSON: "
                '{"document_type": "one of invoice, receipt, purchase_order, '
                'packing_list, bill_of_lading, customs_form, contract, other"}'
            )
            contents = self._build_chunk_contents(client, prompt, first_chunk_pdf_bytes)
            response = client.models.generate_content(
                model=self.classify_model,
                contents=contents,
                config={"temperature": 0.0, "response_mime_type": "application/json"},
            )
            raw = self._clean_json_response(response.text)
            parsed = json.loads(raw)
            return normalize_document_type(parsed.get("document_type"))
        except Exception as exc:
            logger.warning("gemini_classify_failed", error=str(exc))
            return "other"

    def extract_chunk(
        self,
        pdf_bytes: bytes,
        *,
        document_type: str,
        start_page: int,
        end_page: int,
        chunk_index: int,
        total_chunks: int,
        total_pages: int,
        extract_tables: bool = True,
        extract_metadata: bool = True,
    ) -> ChunkExtractionResult:
        """Extract a single page-range chunk. Synchronous (run via
        asyncio.to_thread by the orchestrator) so chunks can be fanned out
        concurrently with asyncio.gather + a semaphore."""
        if not self.api_key:
            raise ExtractionError(
                "GEMINI_API_KEY is not configured. Set it in the environment to enable Gemini extraction."
            )

        try:
            import google.genai as genai
        except ImportError:
            raise ExtractionError("Gemini library not installed: pip install google-genai")

        raw: str | None = None
        request_id = f"chunk-{chunk_index}-{start_page}-{end_page}"
        logger.info(
            "extraction_chunk_request_start",
            request_id=request_id,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            pages=f"{start_page}-{end_page}",
        )
        try:
            client = genai.Client(api_key=self.api_key)
            prompt = self._build_chunk_extraction_prompt(
                document_type=document_type,
                start_page=start_page,
                end_page=end_page,
                chunk_index=chunk_index,
                total_chunks=total_chunks,
                total_pages=total_pages,
                extract_tables=extract_tables,
                extract_metadata=extract_metadata,
            )
            contents = self._build_chunk_contents(client, prompt, pdf_bytes)

            response = client.models.generate_content(
                model=self.model,
                contents=contents,
                config={"temperature": 0.0, "response_mime_type": "application/json"},
            )

            raw = self._clean_json_response(response.text)
            parsed = json.loads(raw)

            local_pages = end_page - start_page + 1

            def _to_global_page(local_page: Any) -> int:
                try:
                    local_page = int(local_page)
                except (TypeError, ValueError):
                    local_page = 1
                local_page = max(1, min(local_page, local_pages))
                return start_page + local_page - 1

            tables = parsed.get("tables", []) or []
            for table in tables:
                if isinstance(table, dict) and "page" in table:
                    table["page"] = _to_global_page(table.get("page"))

            field_pages_local = parsed.get("field_pages", {}) or {}
            field_pages_global = {k: _to_global_page(v) for k, v in field_pages_local.items()}

            logger.info(
                "extraction_chunk_request_complete",
                request_id=request_id,
                chunk_index=chunk_index,
                total_chunks=total_chunks,
                pages=f"{start_page}-{end_page}",
                fields_found=len(parsed.get("extracted_fields") or {}),
                progress_pct=round((chunk_index + 1) / total_chunks * 100, 1),
            )

            return ChunkExtractionResult(
                chunk_index=chunk_index,
                start_page=start_page,
                end_page=end_page,
                total_chunks=total_chunks,
                success=True,
                full_text=parsed.get("full_text", ""),
                tables=tables,
                extracted_fields=parsed.get("extracted_fields", {}) or {},
                field_confidence=parsed.get("field_confidence", {}) or {},
                field_pages=field_pages_global,
                document_type=normalize_document_type(parsed.get("document_type") or document_type),
                language=str(parsed.get("language") or "en").lower(),
                confidence=float(parsed.get("confidence", 0.85) or 0.85),
                word_count=int(parsed.get("word_count", 0) or 0),
            )
        except json.JSONDecodeError as e:
            logger.error("extraction_chunk_json_error", request_id=request_id, error=str(e), raw_response=raw)
            raise ExtractionError(f"Gemini returned invalid JSON for pages {start_page}-{end_page}: {e}")
        except genai.errors.APIError as e:
            code = getattr(e, "code", None)
            msg_lower = str(e).lower()
            logger.error("extraction_chunk_api_error", request_id=request_id, code=code, error=str(e))
            if code == 401 or code == 403:
                raise ExtractionError("Gemini API authentication failed: invalid or unauthorized API key.")
            if code == 429:
                is_billing = "prepayment" in msg_lower or "credits are depleted" in msg_lower or "manage your project and billing" in msg_lower
                if is_billing:
                    raise ExtractionError("Gemini API quota exhausted. Your prepayment credits are depleted — please top up your Google AI Studio balance to continue.")
                raise ExtractionError("Gemini API rate limit reached. Please wait a moment and try again.")
            if code and code >= 500:
                raise ExtractionError(f"Gemini API service error ({code}). Please retry later.")
            raise ExtractionError(f"Gemini extraction failed for pages {start_page}-{end_page}: {e}")
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            logger.error("extraction_chunk_network_error", request_id=request_id, error=str(e))
            raise ExtractionError(f"Network error contacting Gemini API: {e}")
        except Exception as e:
            logger.error("extraction_chunk_error", request_id=request_id, error=str(e))
            raise ExtractionError(f"Gemini extraction failed for pages {start_page}-{end_page}: {e}")

    def _build_chunk_contents(self, client: Any, prompt: str, pdf_bytes: bytes) -> List[Any]:
        import google.genai as genai

        uploaded = client.files.upload(
            file=io.BytesIO(pdf_bytes),
            config={"mime_type": "application/pdf"},
        )
        part = genai.types.Part.from_uri(file_uri=uploaded.uri, mime_type="application/pdf")
        return [prompt, part]

    def _build_chunk_extraction_prompt(
        self,
        *,
        document_type: str,
        start_page: int,
        end_page: int,
        chunk_index: int,
        total_chunks: int,
        total_pages: int,
        extract_tables: bool,
        extract_metadata: bool,
    ) -> str:
        guidance = schema_guidance_for(document_type)
        base = self._build_extraction_prompt(extract_tables, extract_metadata)
        context = f"""You are processing PAGES {start_page}-{end_page} of a {total_pages}-page document \
(this is chunk {chunk_index + 1} of {total_chunks}). This excerpt may be only part of the full document — \
do not assume content missing from this excerpt does not exist elsewhere in the document, and do not fabricate \
fields that are not actually printed on these pages.

{guidance}

"""
        addendum = """
Additional rules for this excerpt:
- Only populate extracted_fields keys that are actually present on PAGES {start}-{end}. Omit keys not found in this excerpt — another chunk may contain them.
- Add a "field_pages" object to the JSON output: for every top-level extracted_fields key you populated, report the page number WITHIN THIS EXCERPT (1 = first page of this excerpt, not the document) where that field's value appears.
- For each entry in "tables", set "page" to the page number WITHIN THIS EXCERPT (1-based), not the absolute document page number.
""".format(start=start_page, end=end_page)
        return context + base + addendum

    def _build_extraction_prompt(
        self, extract_tables: bool, extract_metadata: bool, document_type: Optional[str] = None
    ) -> str:
        guidance = schema_guidance_for(document_type)
        prompt = """You are a document extraction engine. Analyze the provided document and extract all relevant information. Return ONLY valid JSON matching the schema below, with no additional text.

Schema:
{
  "full_text": "Complete extracted text from the document, preserving reading order",
  "page_count": <integer>,
  "word_count": <integer>,
  "language": "Detected language code (e.g., en, es, fr)",
  "document_type": "Document classification (invoice, receipt, purchase_order, bill_of_lading, customs_form, contract, report, letter, memo, other)",
  "confidence": <float 0-1>,
  "tables": [
    {
      "page": <integer>,
      "table_index": <integer>,
      "headers": ["col1", "col2", ...],
      "rows": [["val1", "val2", ...], ...]
    }
  ],
  "metadata": {
    "title": "...",
    "author": "...",
    "creation_date": "...",
    "subject": "..."
  },
  "extracted_fields": {
    "invoice_number": "...",
    "reference_number": "...",
    "purchase_order": "...",
    "vendor_name": "...",
    "vendor_address": "...",
    "vendor_phone": "...",
    "vendor_email": "...",
    "vendor_tax_id": "... (GSTIN/VAT/Tax ID of the vendor)",
    "customer_name": "...",
    "customer_address": "...",
    "customer_phone": "...",
    "customer_tax_id": "... (GSTIN/VAT/Tax ID of the customer)",
    "invoice_date": "... (ISO 8601 date, YYYY-MM-DD)",
    "due_date": "... (ISO 8601 date, YYYY-MM-DD)",
    "currency": "... (ISO 4217 code, e.g. INR, USD)",
    "gross_amount": ...,
    "discount_amount": ...,
    "subtotal": ...,
    "taxable_value": ...,
    "tax_total": ...,
    "cgst_amount": ...,
    "sgst_amount": ...,
    "igst_amount": ...,
    "total_amount": ...,
    "line_items": [
      {
        "description": "...",
        "hsn_code": "...",
        "batch_number": "...",
        "expiry_date": "...",
        "quantity": ...,
        "mrp": ...,
        "unit_price": ...,
        "total": ...
      }
    ],
    "bank_details": {
      "bank_name": "...",
      "account_number": "...",
      "ifsc_code": "...",
      "swift_code": "..."
    },
    "customs_declaration": {
      "hsn_codes": ["..."],
      "country_of_origin": "...",
      "country_of_destination": "...",
      "shipping_terms": "...",
      "port_of_loading": "...",
      "port_of_discharge": "...",
      "gross_weight": ...,
      "net_weight": ...,
      "container_number": "...",
      "bill_of_lading": "..."
    },
    "additional_fields": {
      "key": "value"
    }
  }
}

Rules:
- Extract ALL text from the document, preserving reading order and page structure.
- Recognize and extract tables accurately, maintaining row/column relationships.
- Extract key-value pairs and named entities.
- Classify the document type accurately.
- Preserve all numerical values, dates, currency amounts, HSN codes, document IDs, invoice numbers, and reference identifiers exactly.
- For multi-page documents, maintain page-level context.
- If the document is not an invoice/receipt, populate extracted_fields with relevant keys for that document type.
- If a field is not present in the document, omit it from the output (do not include null or empty values).
- Handle multi-language documents and identify the primary language.
- For customs and trade documents, extract all relevant fields including HS codes, weights, shipping info."""

        if document_type:
            # Append type-specific guidance first so the model knows which
            # fields actually matter for this document.
            prompt = guidance + "\n\n" + prompt

        if extract_tables:
            prompt += "\n- Extract ALL tables from the document with accurate headers and data rows."

        if extract_metadata:
            prompt += "\n- Extract document metadata including title, author, creation date, and subject."

        return prompt

    # ── Text-only extraction (Surya OCR pipeline) ───────────────────────────
    # These methods receive pre-extracted OCR text and send it to Gemini as
    # plain text — no PDF file upload, no client.files.upload() call.

    def classify_from_text(self, ocr_text: str) -> str:
        """Classify document type from OCR text (no file upload).
        Used after Surya OCR so Gemini never sees a raw PDF."""
        if not self.api_key:
            return "other"
        try:
            import google.genai as genai
        except ImportError:
            return "other"

        try:
            client = genai.Client(api_key=self.api_key)
            prompt = (
                "Based on the following document text, classify the document type. "
                'Return ONLY valid JSON: {"document_type": "one of invoice, receipt, '
                'purchase_order, packing_list, bill_of_lading, customs_form, contract, other"}\n\n'
                f"DOCUMENT TEXT (first 3000 chars):\n{ocr_text[:3000]}"
            )
            response = client.models.generate_content(
                model=self.classify_model,
                contents=[prompt],
                config={"temperature": 0.0, "response_mime_type": "application/json"},
            )
            raw = self._clean_json_response(response.text)
            parsed = json.loads(raw)
            return normalize_document_type(parsed.get("document_type"))
        except Exception as exc:
            logger.warning("gemini_classify_from_text_failed", error=str(exc))
            return "other"

    def extract_chunk_from_text(
        self,
        ocr_text: str,
        tables: List[Dict[str, Any]],
        *,
        document_type: str,
        start_page: int,
        end_page: int,
        chunk_index: int,
        total_chunks: int,
        total_pages: int,
        extract_tables: bool = True,
        extract_metadata: bool = True,
    ) -> "ChunkExtractionResult":
        """Extract fields from pre-OCR'd text — no PDF file upload.

        Receives plain text (from PyMuPDF or Surya) and any pre-extracted
        tables, builds a text-only prompt, and calls Gemini 2.5 Pro for
        semantic field extraction. Returns the same ChunkExtractionResult
        as extract_chunk() so the merge engine is unchanged."""
        if not self.api_key:
            raise ExtractionError(
                "GEMINI_API_KEY is not configured."
            )
        try:
            import google.genai as genai
        except ImportError:
            raise ExtractionError("Gemini library not installed: pip install google-genai")

        raw: str | None = None
        request_id = f"chunk-text-{chunk_index}-{start_page}-{end_page}"
        logger.info(
            "extraction_text_chunk_start",
            request_id=request_id,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            pages=f"{start_page}-{end_page}",
            text_chars=len(ocr_text),
        )

        try:
            client = genai.Client(api_key=self.api_key)
            prompt = self._build_chunk_text_extraction_prompt(
                ocr_text=ocr_text,
                tables=tables,
                document_type=document_type,
                start_page=start_page,
                end_page=end_page,
                chunk_index=chunk_index,
                total_chunks=total_chunks,
                total_pages=total_pages,
                extract_tables=extract_tables,
                extract_metadata=extract_metadata,
            )
            response = client.models.generate_content(
                model=self.model,
                contents=[prompt],
                config={"temperature": 0.0, "response_mime_type": "application/json"},
            )

            raw = self._clean_json_response(response.text)
            parsed = json.loads(raw)

            local_pages = end_page - start_page + 1

            def _to_global_page(local_page: Any) -> int:
                try:
                    local_page = int(local_page)
                except (TypeError, ValueError):
                    local_page = 1
                local_page = max(1, min(local_page, local_pages))
                return start_page + local_page - 1

            parsed_tables = parsed.get("tables", []) or []
            for table in parsed_tables:
                if isinstance(table, dict) and "page" in table:
                    table["page"] = _to_global_page(table.get("page"))

            field_pages_local = parsed.get("field_pages", {}) or {}
            field_pages_global = {k: _to_global_page(v) for k, v in field_pages_local.items()}

            logger.info(
                "extraction_text_chunk_complete",
                request_id=request_id,
                chunk_index=chunk_index,
                total_chunks=total_chunks,
                pages=f"{start_page}-{end_page}",
                fields_found=len(parsed.get("extracted_fields") or {}),
                progress_pct=round((chunk_index + 1) / total_chunks * 100, 1),
            )

            return ChunkExtractionResult(
                chunk_index=chunk_index,
                start_page=start_page,
                end_page=end_page,
                total_chunks=total_chunks,
                success=True,
                full_text=parsed.get("full_text", "") or ocr_text,
                tables=parsed_tables,
                extracted_fields=parsed.get("extracted_fields", {}) or {},
                field_confidence=parsed.get("field_confidence", {}) or {},
                field_pages=field_pages_global,
                document_type=normalize_document_type(parsed.get("document_type") or document_type),
                language=str(parsed.get("language") or "en").lower(),
                confidence=float(parsed.get("confidence", 0.85) or 0.85),
                word_count=int(parsed.get("word_count", 0) or 0),
            )

        except json.JSONDecodeError as e:
            logger.error("extraction_text_chunk_json_error", request_id=request_id, error=str(e), raw=raw)
            raise ExtractionError(f"Gemini returned invalid JSON for pages {start_page}-{end_page}: {e}")
        except genai.errors.APIError as e:
            code = getattr(e, "code", None)
            msg_lower = str(e).lower()
            logger.error("extraction_text_chunk_api_error", request_id=request_id, code=code, error=str(e))
            if code in (401, 403):
                raise ExtractionError("Gemini API authentication failed.")
            if code == 429:
                is_billing = "prepayment" in msg_lower or "credits are depleted" in msg_lower or "manage your project and billing" in msg_lower
                if is_billing:
                    raise ExtractionError("Gemini API quota exhausted. Your prepayment credits are depleted — please top up your Google AI Studio balance to continue.")
                raise ExtractionError("Gemini API rate limit reached. Please wait a moment and try again.")
            if code and code >= 500:
                raise ExtractionError(f"Gemini API service error ({code}). Please retry later.")
            raise ExtractionError(f"Gemini extraction failed for pages {start_page}-{end_page}: {e}")
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            logger.error("extraction_text_chunk_network_error", request_id=request_id, error=str(e))
            raise ExtractionError(f"Network error contacting Gemini API: {e}")
        except Exception as e:
            logger.error("extraction_text_chunk_error", request_id=request_id, error=str(e))
            raise ExtractionError(f"Gemini extraction failed for pages {start_page}-{end_page}: {e}")

    def _build_chunk_text_extraction_prompt(
        self,
        *,
        ocr_text: str,
        tables: List[Dict[str, Any]],
        document_type: str,
        start_page: int,
        end_page: int,
        chunk_index: int,
        total_chunks: int,
        total_pages: int,
        extract_tables: bool,
        extract_metadata: bool,
    ) -> str:
        """Build a text-only extraction prompt embedding the OCR content inline."""
        guidance = schema_guidance_for(document_type)
        base = self._build_extraction_prompt(extract_tables, extract_metadata)

        table_section = ""
        if tables:
            table_section = "\n\nPRE-EXTRACTED TABLES (from PyMuPDF):\n"
            for t in tables:
                headers = t.get("headers", [])
                rows = t.get("rows", [])
                table_section += f"\nTable {t.get('table_index', 0) + 1} (page {t.get('page', start_page)}):\n"
                if headers:
                    table_section += " | ".join(str(h) for h in headers) + "\n"
                    table_section += "-" * max(40, 7 * len(headers)) + "\n"
                for row in rows[:50]:
                    table_section += " | ".join(str(c) for c in row) + "\n"

        context = (
            f"You are processing PAGES {start_page}-{end_page} of a {total_pages}-page document "
            f"(chunk {chunk_index + 1} of {total_chunks}).\n\n"
            "IMPORTANT: The text below was already extracted by an OCR engine (PyMuPDF or Surya OCR). "
            "Do NOT perform additional OCR. Extract structured fields directly from this pre-extracted text.\n\n"
            f"{guidance}\n\n"
            f"PRE-EXTRACTED OCR TEXT:\n{ocr_text}"
            f"{table_section}\n\n"
            f"{base}\n\n"
            f"Additional rules for this excerpt:\n"
            f"- Only populate extracted_fields keys actually present in the OCR text above. "
            f"Omit keys not found — another chunk may contain them.\n"
            f"- Add a \"field_pages\" object: for each populated top-level extracted_fields key, "
            f"report the page number WITHIN THIS EXCERPT (1 = page {start_page}, 2 = page {start_page + 1}, etc.).\n"
            f"- For tables entries, set \"page\" to the page within this excerpt (1-based).\n"
            f"- Set full_text to empty string \"\". The orchestrator already has the raw OCR "
            f"text directly; do not echo it back in the response (it wastes output tokens).\n"
            f"- Do not invent values not present in the OCR text."
        )
        return context

    def get_supported_formats(self) -> List[str]:
        return self.supported_mimes
