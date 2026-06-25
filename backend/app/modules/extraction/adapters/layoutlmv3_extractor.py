from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from .base import BaseExtractor, ExtractionResult, ExtractionError

logger = logging.getLogger("translatrix.extraction.layoutlmv3")

# Map from model label names to our field schema
_LABEL_TO_FIELD: dict[str, str] = {
    "invoice_number": "invoiceNumber",
    "invoice_num": "invoiceNumber",
    "invoice_date": "invoiceDate",
    "due_date": "dueDate",
    "vendor_name": "vendor",
    "vendor": "vendor",
    "biller_name": "vendor",
    "vendor_addr": "vendorAddress",
    "vendor_address": "vendorAddress",
    "biller_address": "vendorAddress",
    "cust_name": "customer",
    "customer": "customer",
    "customer_name": "customer",
    "cust_addr": "customerAddress",
    "customer_address": "customerAddress",
    "total": "total",
    "total_amount": "total",
    "subtotal": "subtotal",
    "tax": "taxAmount",
    "tax_amount": "taxAmount",
    "cgst": "cgstAmount",
    "cgst_amount": "cgstAmount",
    "sgst": "sgstAmount",
    "sgst_amount": "sgstAmount",
    "igst": "igstAmount",
    "igst_amount": "igstAmount",
    "gst": "taxAmount",
    "gst_amount": "taxAmount",
    "discount": "discountAmount",
    "discount_amount": "discountAmount",
    "tax_rate": "taxRate",
    "gst_rate": "taxRate",
    "mrp": "mrp",
    "rate": "rate",
    "unit_price": "rate",
    "unitprice": "rate",
    "gst_percent": "gst",
    "gst%": "gst",
    "tax_percent": "gst",
    "tax%": "gst",
    "taxable_value": "taxable_value",
    "taxablevalue": "taxable_value",
    "assessable_value": "taxable_value",
}


def _normalise_label(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")


class LayoutLMv3Extractor(BaseExtractor):
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self._processor = None
        self._model = None
        self._id2label: dict[int, str] = {}
        self.supported_mimes = [
            "application/pdf", "image/png", "image/jpeg", "image/tiff",
        ]

    def _load_model(self):
        if self._model is not None:
            return
        try:
            from transformers import (
                LayoutLMv3Processor,
                LayoutLMv3ForTokenClassification,
            )
            model_name = self.config.get(
                "layoutlmv3_model",
                "Theivaprakasham/layoutlmv3-finetuned-invoice",
            )
            self._processor = LayoutLMv3Processor.from_pretrained(
                model_name, apply_ocr=True
            )
            self._model = LayoutLMv3ForTokenClassification.from_pretrained(model_name)
            self._model.eval()
            self._id2label = self._model.config.id2label
            logger.info("layoutlmv3_model_loaded", model=model_name)
        except Exception as exc:
            logger.warning("layoutlmv3_load_failed", error=str(exc))
            raise ExtractionError(f"LayoutLMv3 model load failed: {exc}")

    def can_extract(self, file_path: Path, mime_type: str) -> bool:
        return mime_type in self.supported_mimes or file_path.suffix.lower() in (
            ".pdf", ".png", ".jpg", ".jpeg", ".tiff",
        )

    def extract_fields_from_image(self, image_path: str | Path) -> dict[str, Any]:
        self._load_model()
        try:
            from PIL import Image
            import torch
        except ImportError:
            logger.error("missing_dependencies")
            return {}

        try:
            image = Image.open(str(image_path)).convert("RGB")
            encoding = self._processor(image, return_tensors="pt")
            with torch.no_grad():
                outputs = self._model(**encoding)
            logits = outputs.logits
            predictions = logits.argmax(-1).squeeze().tolist()
            if isinstance(predictions, int):
                predictions = [predictions]
            input_ids = encoding.input_ids.squeeze().tolist()
            if isinstance(input_ids, int):
                input_ids = [input_ids]
            tokens = self._processor.tokenizer.convert_ids_to_tokens(input_ids)
            return self._merge_bio(tokens, predictions)
        except Exception as exc:
            logger.warning("layoutlmv3_inference_failed", error=str(exc))
            return {}

    def _merge_bio(
        self, tokens: list[str], predictions: list[int]
    ) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        current_label: str | None = None
        current_parts: list[str] = []

        for token, pred_id in zip(tokens, predictions):
            label_str = self._id2label.get(pred_id, "O")
            if label_str == "O":
                if current_label:
                    text = " ".join(current_parts).replace(" ##", "")
                    field_key = _LABEL_TO_FIELD.get(
                        _normalise_label(current_label)
                    )
                    if field_key and not fields.get(field_key):
                        fields[field_key] = text
                    current_label = None
                    current_parts = []
                continue
            if label_str.startswith("B-"):
                if current_label:
                    text = " ".join(current_parts).replace(" ##", "")
                    field_key = _LABEL_TO_FIELD.get(
                        _normalise_label(current_label)
                    )
                    if field_key and not fields.get(field_key):
                        fields[field_key] = text
                current_label = label_str[2:]
                current_parts = [token]
            elif label_str.startswith("I-") and current_label:
                current_label = label_str[2:]
                current_parts.append(token)
            else:
                if current_label:
                    text = " ".join(current_parts).replace(" ##", "")
                    field_key = _LABEL_TO_FIELD.get(
                        _normalise_label(current_label)
                    )
                    if field_key and not fields.get(field_key):
                        fields[field_key] = text
                current_label = None
                current_parts = []

        if current_label:
            text = " ".join(current_parts).replace(" ##", "")
            field_key = _LABEL_TO_FIELD.get(_normalise_label(current_label))
            if field_key and not fields.get(field_key):
                fields[field_key] = text

        fields["_source"] = "layoutlmv3"
        return fields

    def extract(
        self,
        file_path: Path,
        extract_tables: bool = True,
        extract_metadata: bool = True,
        **kwargs,
    ) -> ExtractionResult:
        raise NotImplementedError(
            "Use extract_fields_from_image() or extract_pdf_fields() directly."
        )

    def extract_pdf_fields(self, pdf_path: str | Path) -> dict[str, Any]:
        try:
            from pdf2image import convert_from_path
        except ImportError:
            logger.error("pdf2image_not_available")
            return {}

        try:
            images = convert_from_path(str(pdf_path), dpi=200, first_page=1, last_page=3)
        except Exception as exc:
            logger.warning("pdf_to_image_failed", error=str(exc))
            return {}

        merged: dict[str, Any] = {}
        for img in images:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                img.save(tmp.name)
                page_fields = self.extract_fields_from_image(tmp.name)
                Path(tmp.name).unlink(missing_ok=True)
            for key, value in page_fields.items():
                if key == "_source":
                    continue
                if key not in merged or merged[key] is None or merged[key] == "":
                    merged[key] = value
        merged["_source"] = "layoutlmv3"
        return merged


def enrich_with_layoutlmv3(
    file_path: Path,
    dtype: str,
    existing_fields: dict[str, Any],
    extractor: LayoutLMv3Extractor | None = None,
) -> dict[str, Any]:
    if dtype not in ("invoice", "receipt", "purchase_order"):
        return existing_fields
    if extractor is None:
        extractor = LayoutLMv3Extractor()
    try:
        lvm3_fields = extractor.extract_pdf_fields(file_path)
        merged = dict(existing_fields)
        for key, value in lvm3_fields.items():
            if key == "_source":
                continue
            existing_val = merged.get(key)
            if existing_val is None or existing_val == "" or existing_val == 0:
                merged[key] = value
        return merged
    except Exception as exc:
        logger.warning("layoutlmv3_enrich_failed", error=str(exc))
        return existing_fields
