"""
Mistral-based fallback extractor for when Gemini extraction fails.
This adapter runs Mistral OCR (via the existing OCR adapters/services),
parses the OCR output, and applies document-type-aware heuristics to
produce a validated extracted_fields dict compatible with the rest of the
pipeline (the same shape produced by Gemini extraction).

It optionally augments extraction with GLiNER (zero-shot NER on OCR text)
and LayoutLMv3 (visual document understanding) for improved accuracy.

It is intentionally defensive and never raises third-party exceptions
— instead it raises ExtractionError only when extraction cannot proceed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import structlog
import time

from .base import BaseExtractor, ExtractionResult, ExtractionError
from app.modules.ocr.adapters.mistral_adapter import MistralOCRProvider
from app.modules.frontend_api import document_intelligence as di
from app.modules.extraction.schema_registry import normalize_document_type

logger = structlog.get_logger(__name__)

# Lazy-loaded GLiNER & LayoutLMv3 enrichments
_gliner_instance = None
_layoutlmv3_instance = None


def _get_gliner():
    global _gliner_instance
    if _gliner_instance is None:
        try:
            from .gliner_extractor import GLiNERExtractor
            _gliner_instance = GLiNERExtractor()
        except Exception as exc:
            logger.warning("gliner_not_available", error=str(exc))
    return _gliner_instance


def _get_layoutlmv3():
    global _layoutlmv3_instance
    if _layoutlmv3_instance is None:
        try:
            from .layoutlmv3_extractor import LayoutLMv3Extractor
            _layoutlmv3_instance = LayoutLMv3Extractor()
        except Exception as exc:
            logger.warning("layoutlmv3_not_available", error=str(exc))
    return _layoutlmv3_instance


class MistralFallbackExtractor(BaseExtractor):
    """Fallback extractor that uses Mistral OCR and deterministic
    document intelligence heuristics to extract fields when Gemini is
    unavailable or fails.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.ocr = MistralOCRProvider({})
        self.supported_mimes = [
            "application/pdf",
            "image/png",
            "image/jpeg",
            "image/tiff",
            "text/plain",
            "application/json",
            "application/xml",
        ]

    def can_extract(self, file_path: Path, mime_type: str) -> bool:
        return mime_type in self.supported_mimes or file_path.suffix.lower() in (".pdf", ".png", ".jpg", ".jpeg", ".tiff")

    def extract(self, file_path: Path, extract_tables: bool = True, extract_metadata: bool = True, *, document_type: Optional[str] = None, **kwargs) -> ExtractionResult:
        t0 = time.time()
        try:
            # Use Mistral OCR to obtain page-wise text and markdown tables
            ocr_result = self.ocr.recognize_pdf(file_path) if file_path.suffix.lower() == ".pdf" else self.ocr.recognize_image(file_path)
        except Exception as exc:
            logger.error("mistral_fallback_ocr_failed", error=str(exc), file=str(file_path))
            raise ExtractionError(f"Mistral OCR failed: {exc}")

        full_text = ocr_result.full_text if hasattr(ocr_result, 'full_text') else ocr_result.text
        # Parse markdown tables from Mistral OCR output
        try:
            from app.modules.frontend_api.document_intelligence import _find_markdown_tables
            raw_tables = _find_markdown_tables(full_text)
            # Also keep the dict format for metadata
            tables_for_metadata: List[Dict[str, Any]] = []
            for ti, tbl in enumerate(raw_tables):
                headers = tbl[0]
                rows = tbl[1:]
                tables_for_metadata.append({"page": 1, "table_index": ti, "headers": headers, "rows": rows})
        except Exception:
            raw_tables = []
            tables_for_metadata = []

        dtype = normalize_document_type(document_type) if document_type else "other"

        # Deterministic field extraction based on document type
        extracted_fields: Dict[str, Any] = {}
        field_confidence: Dict[str, float] = {}
        field_pages: Dict[str, int] = {}

        avg_conf = getattr(ocr_result, 'average_confidence', getattr(ocr_result, 'overall_confidence', 0.8))

        if dtype == "invoice":
            try:
                fields = di.extract_financial_fields(full_text, tables=raw_tables)
                trade = di.extract_trade_fields(full_text)
                extracted_fields = {
                    "invoice_number": fields.get("invoiceNumber"),
                    "invoice_date": fields.get("invoiceDate"),
                    "due_date": fields.get("dueDate"),
                    "vendor_name": fields.get("vendor"),
                    "vendor_address": fields.get("vendorAddress"),
                    "vendor_phone": fields.get("vendorPhone"),
                    "vendor_email": fields.get("vendorEmail"),
                    "vendor_pan": fields.get("vendorPan"),
                    "customer_name": fields.get("customer"),
                    "customer_gstin": fields.get("customerGstin"),
                    "customer_address": fields.get("customerAddress"),
                    "customer_phone": fields.get("customerPhone"),
                    "customer_email": fields.get("customerEmail"),
                    "customer_pan": fields.get("customerPan"),
                    "gst_vat_number": fields.get("gstVatNumber"),
                    "currency": fields.get("currency"),
                    "subtotal": fields.get("subtotal"),
                    "tax_total": fields.get("taxAmount"),
                    "total_amount": fields.get("total"),
                    "line_items": fields.get("lineItems"),
                    "cgst_amount": fields.get("cgstAmount"),
                    "sgst_amount": fields.get("sgstAmount"),
                    "igst_amount": fields.get("igstAmount"),
                    "taxable_value": fields.get("taxableValue"),
                    "gross_amount": fields.get("grossAmount"),
                    "discount_amount": fields.get("discountAmount"),
                    "place_of_supply": fields.get("placeOfSupply"),
                    "reverse_charge": fields.get("reverseCharge"),
                    "tax_rates": fields.get("taxRates"),
                    "tax_rate": fields.get("taxRate"),
                    "reference_number": fields.get("referenceNumber"),
                    "exporter": trade.get("exporter"),
                    "importer": trade.get("importer"),
                    "buyer": trade.get("buyer"),
                    "seller": trade.get("seller"),
                    "incoterms": trade.get("incoterms"),
                    "country_of_origin": trade.get("countryOfOrigin"),
                    "country_of_destination": trade.get("countryOfDestination"),
                    "port_of_loading": trade.get("portOfLoading"),
                    "port_of_discharge": trade.get("portOfDischarge"),
                    "gross_weight": trade.get("grossWeight"),
                    "net_weight": trade.get("netWeight"),
                    "payment_terms": trade.get("paymentTerms"),
                    "invoice_value": trade.get("invoiceValue"),
                    "additional_fields": {},
                }
                for k in list(extracted_fields.keys()):
                    field_confidence[k] = float(avg_conf or 0.5)
            except Exception as exc:
                logger.warning("mistral_invoice_parse_failed", error=str(exc))
        elif dtype == "banking_document":
            try:
                banking = di.extract_banking_statement_fields(full_text)
                extracted_fields = {
                    "bank_name": banking.get("bankName"),
                    "branch_name": banking.get("branchName"),
                    "account_holder_name": banking.get("accountHolderName"),
                    "account_number": banking.get("accountNumber"),
                    "account_type": banking.get("accountType"),
                    "statement_period_from": banking.get("statementPeriodFrom"),
                    "statement_period_to": banking.get("statementPeriodTo"),
                    "currency": banking.get("currency"),
                    "opening_balance": banking.get("openingBalance"),
                    "closing_balance": banking.get("closingBalance"),
                    "transactions": banking.get("transactions", []),
                    "additional_fields": {},
                }
                for k in list(extracted_fields.keys()):
                    field_confidence[k] = float(avg_conf or 0.5)
            except Exception as exc:
                logger.warning("mistral_banking_parse_failed", error=str(exc))
        else:
            extracted_fields = {}
            field_confidence = {}

        # Enrich with GLiNER (zero-shot NER on OCR text)
        gliner = _get_gliner()
        if gliner and extracted_fields:
            try:
                from .gliner_extractor import enrich_with_gliner
                extracted_fields = enrich_with_gliner(
                    full_text, dtype, extracted_fields, gliner, threshold=0.5
                )
            except Exception as exc:
                logger.warning("gliner_enrich_failed", error=str(exc))

        # Enrich with LayoutLMv3 (visual document understanding on PDF/image)
        lvm3 = _get_layoutlmv3()
        if lvm3 and dtype in ("invoice", "receipt", "purchase_order"):
            try:
                from .layoutlmv3_extractor import enrich_with_layoutlmv3
                extracted_fields = enrich_with_layoutlmv3(
                    file_path, dtype, extracted_fields, lvm3
                )
            except Exception as exc:
                logger.warning("layoutlmv3_enrich_failed", error=str(exc))

        metadata = {
            "document_type": dtype,
            "provider": "mistral_fallback",
            "model": getattr(self.ocr, 'model', 'mistral-ocr'),
            "extracted_fields": extracted_fields,
            "field_confidence": field_confidence,
            "field_pages": field_pages,
        }

        elapsed_ms = int((time.time() - t0) * 1000)
        metadata["extraction_time_ms"] = elapsed_ms

        logger.info("mistral_fallback_extraction_complete", document_type=dtype, pages=ocr_result.pages.__len__() if hasattr(ocr_result, 'pages') else 1, elapsed_ms=elapsed_ms)

        return ExtractionResult(
            text=full_text,
            tables=tables_for_metadata,
            metadata=metadata,
            page_count=getattr(ocr_result, 'total_pages', getattr(ocr_result, 'pages', None) and len(ocr_result.pages) or 1),
            confidence=float(getattr(ocr_result, 'overall_confidence', getattr(ocr_result, 'average_confidence', 0.85)) or 0.85),
            word_count=len(full_text.split()) if full_text else 0,
        )
