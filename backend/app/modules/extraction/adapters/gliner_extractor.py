from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .base import BaseExtractor, ExtractionResult, ExtractionError

logger = logging.getLogger("translatrix.extraction.gliner")

_INVOICE_LABELS = [
    "vendor name", "vendor address", "customer name", "customer address",
    "invoice number", "invoice date", "due date",
    "gstin", "pan", "phone number", "email",
    "total amount", "subtotal", "tax amount", "discount amount",
    "cgst amount", "sgst amount", "igst amount", "gst amount",
    "tax rate", "gst rate",
    "place of supply", "reverse charge",
    "product name", "item description", "product description", "item name",
    "hsn code", "quantity", "unit price", "line total",
    "mrp", "rate", "gst percent", "tax percent",
    "cgst", "sgst", "igst", "taxable value",
    "bank name", "account number", "ifsc code",
]

_BANKING_LABELS = [
    "bank name", "branch name", "account holder name",
    "account number", "account type", "ifsc code",
    "statement period", "opening balance", "closing balance",
]


class GLiNERExtractor(BaseExtractor):
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self._model = None
        self.supported_mimes = [
            "application/pdf", "image/png", "image/jpeg",
            "image/tiff", "text/plain",
        ]

    def _load_model(self):
        if self._model is not None:
            return
        try:
            from gliner import GLiNER
            model_name = self.config.get("gliner_model", "urchade/gliner_medium-v2.1")
            self._model = GLiNER.from_pretrained(model_name)
            logger.info("gliner_model_loaded", model=model_name)
        except Exception as exc:
            logger.error("gliner_load_failed", error=str(exc))
            raise ExtractionError(f"GLiNER model load failed: {exc}")

    def can_extract(self, file_path: Path, mime_type: str) -> bool:
        return mime_type in self.supported_mimes or file_path.suffix.lower() in (".pdf", ".png", ".jpg", ".jpeg", ".tiff")

    def extract_entities(self, text: str, labels: list[str], threshold: float = 0.5) -> dict[str, list[dict[str, Any]]]:
        self._load_model()
        entities = self._model.predict_entities(text, labels, threshold=threshold)
        result: dict[str, list[dict[str, Any]]] = {}
        for ent in entities:
            label = ent.get("label", "unknown")
            result.setdefault(label, []).append({
                "text": ent.get("text", ""),
                "score": ent.get("score", 0.0),
                "start": ent.get("start", 0),
                "end": ent.get("end", 0),
            })
        return result

    def _pick_best(self, entities: list[dict[str, Any]]) -> str | None:
        if not entities:
            return None
        best = max(entities, key=lambda e: e.get("score", 0))
        return best["text"]

    def _map_to_fields(self, grouped: dict[str, list[dict[str, Any]]], dtype: str) -> dict[str, Any]:
        fields: dict[str, Any] = {}

        def pick(label: str) -> str | None:
            return self._pick_best(grouped.get(label, []))

        if dtype == "invoice":
            v = pick("vendor name")
            if v:
                fields["vendor"] = v
            v = pick("vendor address")
            if v:
                fields["vendorAddress"] = v
            v = pick("customer name")
            if v:
                fields["customer"] = v
            v = pick("customer address")
            if v:
                fields["customerAddress"] = v
            v = pick("invoice number")
            if v:
                fields["invoiceNumber"] = v
            v = pick("invoice date")
            if v:
                fields["invoiceDate"] = v
            v = pick("due date")
            if v:
                fields["dueDate"] = v
            v = pick("gstin")
            if v:
                fields["gstVatNumber"] = v
            v = pick("pan")
            if v:
                fields["vendorPan"] = v
            v = pick("phone number")
            if v:
                fields["vendorPhone"] = v
            v = pick("email")
            if v:
                fields["vendorEmail"] = v
            v = pick("total amount")
            if v:
                try:
                    fields["total"] = float(v.replace(",", ""))
                except (ValueError, TypeError):
                    fields["total"] = v
            v = pick("subtotal")
            if v:
                try:
                    fields["subtotal"] = float(v.replace(",", ""))
                except (ValueError, TypeError):
                    fields["subtotal"] = v
            v = pick("tax amount")
            if v:
                try:
                    fields["taxAmount"] = float(v.replace(",", ""))
                except (ValueError, TypeError):
                    fields["taxAmount"] = v
            v = pick("cgst amount")
            if v:
                try:
                    fields["cgstAmount"] = float(v.replace(",", ""))
                except (ValueError, TypeError):
                    fields["cgstAmount"] = v
            v = pick("sgst amount")
            if v:
                try:
                    fields["sgstAmount"] = float(v.replace(",", ""))
                except (ValueError, TypeError):
                    fields["sgstAmount"] = v
            v = pick("igst amount")
            if v:
                try:
                    fields["igstAmount"] = float(v.replace(",", ""))
                except (ValueError, TypeError):
                    fields["igstAmount"] = v
            v = pick("gst amount")
            if v:
                try:
                    fields["taxAmount"] = float(v.replace(",", ""))
                except (ValueError, TypeError):
                    fields["taxAmount"] = v
            v = pick("tax rate")
            if v:
                try:
                    fields["taxRate"] = float(v.replace("%", "").replace(",", ""))
                except (ValueError, TypeError):
                    fields["taxRate"] = v
            v = pick("gst rate")
            if v:
                try:
                    fields["taxRate"] = float(v.replace("%", "").replace(",", ""))
                except (ValueError, TypeError):
                    fields["taxRate"] = v
            v = pick("discount amount")
            if v:
                try:
                    fields["discountAmount"] = float(v.replace(",", ""))
                except (ValueError, TypeError):
                    fields["discountAmount"] = v
            v = pick("place of supply")
            if v:
                fields["placeOfSupply"] = v
            v = pick("reverse charge")
            if v:
                fields["reverseCharge"] = v.lower() in ("yes", "y", "true", "applicable")
        elif dtype == "banking_document":
            v = pick("bank name")
            if v:
                fields["bankName"] = v
            v = pick("branch name")
            if v:
                fields["branchName"] = v
            v = pick("account holder name")
            if v:
                fields["accountHolderName"] = v
            v = pick("account number")
            if v:
                fields["accountNumber"] = v
            v = pick("account type")
            if v:
                fields["accountType"] = v
            v = pick("ifsc code")
            if v:
                fields["ifscSwiftCode"] = v

        fields["_source"] = "gliner"
        return fields

    def extract(
        self,
        file_path: Path,
        extract_tables: bool = True,
        extract_metadata: bool = True,
        **kwargs,
    ) -> ExtractionResult:
        raise NotImplementedError("GLiNERExtractor works on text input, not files. Use extract_entities() directly.")


def enrich_with_gliner(
    text: str,
    dtype: str,
    existing_fields: dict[str, Any],
    gliner_extractor: GLiNERExtractor | None = None,
    threshold: float = 0.5,
) -> dict[str, Any]:
    if gliner_extractor is None:
        gliner_extractor = GLiNERExtractor()
    try:
        labels = _INVOICE_LABELS if dtype == "invoice" else _BANKING_LABELS if dtype == "banking_document" else []
        if not labels:
            return existing_fields
        grouped = gliner_extractor.extract_entities(text, labels, threshold=threshold)
        gliner_fields = gliner_extractor._map_to_fields(grouped, dtype)
        merged = dict(existing_fields)
        for key, value in gliner_fields.items():
            if key == "_source":
                continue
            existing_val = merged.get(key)
            if existing_val is None or existing_val == "" or existing_val == 0:
                merged[key] = value
            elif key in ("vendor", "customer", "vendorAddress", "customerAddress", "vendorPhone", "vendorEmail"):
                if not existing_val or len(str(existing_val)) < 3:
                    merged[key] = value
        return merged
    except Exception as exc:
        logger.warning("gliner_enrich_failed", error=str(exc))
        return existing_fields
