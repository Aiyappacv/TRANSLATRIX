from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.modules.frontend_api.extraction_json import (
    ExtractionJSON,
    FieldConfidence,
    FinancialSummary,
    LineItem,
    TradeFields,
    TransactionInfo,
    BankingInfo,
    Metadata,
    InvoiceDetails,
    SupplierInfo,
    CustomerInfo,
    ProcessingMetrics,
    ValidationResult,
    MultiPageDocument,
    _strip_nulls,
    now_iso,
)
from app.modules.frontend_api.store import get_state, set_state, scope_for_user

logger = logging.getLogger("translatrix.export.json")

_CONFIDENCE_ADJUSTMENTS: dict[str, float] = {
    "invoice_number": 0.05,
    "gst_vat": 0.03,
    "invoice_date": 0.04,
    "total": 0.02,
    "subtotal": 0.03,
    "vendor": 0.08,
    "customer": 0.08,
    "currency": 0.01,
    "tax_amount": 0.06,
    "line_items": 0.10,
    "vendor_address": 0.10,
    "vendor_phone": 0.12,
    "vendor_email": 0.12,
    "customer_address": 0.10,
    "customer_phone": 0.12,
    "hsn_code": 0.08,
    "batch_number": 0.10,
    "expiry_date": 0.10,
}

SAP_FIELD_MAPPING: dict[str, str] = {
    "supplier.name": "LIFNR",
    "supplier.gstin": "STCEG",
    "supplier.address": "STRAS",
    "customer.name": "KUNNR",
    "customer.gstin": "STCEG",
    "invoice_details.invoice_number": "BELNR",
    "invoice_details.invoice_date": "BLDAT",
    "invoice_details.document_type": "BLART",
    "invoice_details.currency": "WAERS",
    "financial_summary.gross_amount": "WRBTR",
    "financial_summary.net_amount": "DMBTR",
    "financial_summary.gst_amount": "MWSTS",
    "financial_summary.discount_amount": "SKFBT",
    "line_items[].product_name": "MAKTX",
    "line_items[].hsn_code": "MFRNR",
    "line_items[].quantity": "MENGE_D",
    "line_items[].rate": "NETPR",
    "line_items[].line_total": "NETWR",
    "metadata.page_count": "ANZBL",
}


def _estimate_field_confidence(
    base_confidence: float,
    field_key: str,
    value: Any,
    source: str | None = None,
) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)) and value == 0:
        return 0.0
    penalty = _CONFIDENCE_ADJUSTMENTS.get(field_key, 0.05)
    source_boost = {"layout": 0.08, "table": 0.10, "regex": 0.0, "llm": 0.12}.get(source or "regex", 0.0)
    adjusted = max(0.0, min(1.0, base_confidence - penalty + source_boost))
    return round(adjusted, 4)


def _build_confidence_details(
    fields: dict[str, Any],
    base_confidence: float,
) -> list[FieldConfidence]:
    # Gemini 2.5 Pro reports its own per-field confidence (how certain the
    # model is that it read each value correctly off the document) — prefer
    # that real score over the heuristic estimate below, which only exists
    # as a fallback for the legacy regex extractor.
    gemini_confidence: dict[str, float] = fields.get("_geminiFieldConfidence") or {}
    gemini_pages: dict[str, int] = fields.get("_geminiFieldPages") or {}
    source = "gemini" if gemini_confidence else "regex"

    detail_keys = [
        ("invoice_number", "invoiceNumber"),
        ("gst_vat_number", "gstVatNumber"),
        ("invoice_date", "invoiceDate"),
        ("due_date", "dueDate"),
        ("vendor", "vendor"),
        ("customer", "customer"),
        ("currency", "currency"),
        ("total", "total"),
        ("subtotal", "subtotal"),
        ("tax_amount", "taxAmount"),
        ("tax_rate", "taxRate"),
        ("reference_number", "referenceNumber"),
    ]
    result = []
    for field_name, field_key in detail_keys:
        value = fields.get(field_key)
        if field_key in gemini_confidence:
            confidence = gemini_confidence[field_key]
        else:
            confidence = _estimate_field_confidence(base_confidence, field_name, value, source)
        if value is None or value == "" or (isinstance(value, (int, float)) and value == 0):
            status = "missing"
        elif confidence < 0.8:
            status = "needs_review"
        else:
            status = "extracted"
        result.append(FieldConfidence(
            field=field_name, value=value, confidence=confidence, status=status, source=source,
            page=gemini_pages.get(field_key),
        ))
    return result


_CONFIDENCE_THRESHOLDS: list[tuple[float, str]] = [
    (0.95, "high"),
    (0.80, "medium"),
    (0.0, "low"),
]


def classify_confidence(score: float) -> str:
    for threshold, label in _CONFIDENCE_THRESHOLDS:
        if score >= threshold:
            return label
    return "low"


def _count_extracted_fields(fields: dict[str, Any]) -> int:
    count = 0
    for key, value in fields.items():
        if key in ("evidence", "lineItems", "taxRates"):
            continue
        if value is not None and value != "" and value != 0 and value != []:
            count += 1
    return count


def build_extraction_json(
    file_record: dict[str, Any],
    fields: dict[str, Any] | None = None,
) -> ExtractionJSON:
    if fields is None:
        fields = file_record.get("structuredFields") or {}

    base_confidence = file_record.get("confidence", 0.0) or 0.0
    ocr_info = file_record.get("ocr") or {}
    metadata_info = file_record.get("_meta") or {}
    processing_info = file_record.get("processingSettings") or {}
    layout_data = file_record.get("layoutAnalysis") or {}
    validation_data = file_record.get("validationResults") or {}

    json_fields = fields if fields else {}

    line_items_data = json_fields.get("lineItems") or []
    line_items_list = []
    for item in line_items_data:
        line_items_list.append(
            LineItem(
                product_name=item.get("description") or item.get("product_name"),
                hsn_code=item.get("hsnCode") or item.get("hsn_code"),
                pack=item.get("pack"),
                batch_number=item.get("batchNumber") or item.get("batch_number"),
                expiry_date=item.get("expiryDate") or item.get("expiry_date"),
                quantity=item.get("quantity"),
                mrp=item.get("mrp"),
                rate=item.get("rate"),
                gst=item.get("gst"),
                taxable_value=item.get("taxableValue") or item.get("taxable_value"),
                cgst=item.get("cgst"),
                sgst=item.get("sgst"),
                igst=item.get("igst"),
                line_total=item.get("lineTotal") or item.get("line_total"),
                confidence=base_confidence,
            )
        )

    total = json_fields.get("total")
    subtotal = json_fields.get("subtotal")
    tax_amount = json_fields.get("taxAmount")
    discount_amount = json_fields.get("discountAmount")
    cgst_amount = json_fields.get("cgstAmount")
    sgst_amount = json_fields.get("sgstAmount")
    igst_amount = json_fields.get("igstAmount")
    taxable_value = json_fields.get("taxableValue")

    confidence = _build_confidence_details(json_fields, base_confidence)

    raw_text = file_record.get("extractedText")

    fields_extracted = _count_extracted_fields(json_fields)
    tables_count = len(layout_data.get("tables", []))
    ocr_pages = ocr_info.get("pageCount", 1)

    processing_time = None
    if ocr_info.get("startedAt") and ocr_info.get("completedAt"):
        try:
            from datetime import datetime
            start = datetime.fromisoformat(ocr_info["startedAt"])
            end = datetime.fromisoformat(ocr_info["completedAt"])
            processing_time = (end - start).total_seconds()
        except Exception:
            pass

    validation_results = []
    for cat in ("valid", "needs_review", "warning"):
        for item in validation_data.get(cat, []):
            validation_results.append(ValidationResult(**item))

    doc_type = (fields.get("documentType") or
                metadata_info.get("documentType") or
                file_record.get("category") or
                "")
    is_invoice = doc_type in ("invoice", "receipt", "purchase_order", "packing_list", "bill_of_lading", "customs_form")
    is_banking = doc_type in ("banking_document",)

    return ExtractionJSON(
        document_id=file_record.get("id"),
        document_type=doc_type,
        document_name=file_record.get("fileName"),
        processing_timestamp=metadata_info.get("processingTimestamp") or now_iso(),
        ocr_engine=ocr_info.get("engine", "PaddleOCR"),
        overall_confidence=min(1.0, base_confidence or 0.0),
        supplier=SupplierInfo(
            name=json_fields.get("vendor"),
            gstin=json_fields.get("gstVatNumber"),
            pan=json_fields.get("vendorPan"),
            address=json_fields.get("vendorAddress"),
            phone=json_fields.get("vendorPhone"),
            email=json_fields.get("vendorEmail"),
        ) if is_invoice else None,
        customer=CustomerInfo(
            name=json_fields.get("customer"),
            pan=json_fields.get("customerPan"),
            gstin=json_fields.get("customerGstin"),
            address=json_fields.get("customerAddress"),
            phone=json_fields.get("customerPhone"),
            email=json_fields.get("customerEmail"),
        ) if is_invoice else None,
        invoice_details=InvoiceDetails(
            invoice_number=json_fields.get("invoiceNumber"),
            invoice_date=json_fields.get("invoiceDate"),
            document_type=doc_type,
            currency=json_fields.get("currency"),
        ) if is_invoice else None,
        financial_summary=FinancialSummary(
            gross_amount=json_fields.get("grossAmount"),
            net_amount=subtotal if subtotal is not None else total,
            gst_amount=tax_amount,
            cgst_amount=cgst_amount,
            sgst_amount=sgst_amount,
            igst_amount=igst_amount,
            discount_amount=discount_amount,
            taxable_value=taxable_value if taxable_value is not None else subtotal,
            place_of_supply=json_fields.get("placeOfSupply"),
            reverse_charge=json_fields.get("reverseCharge"),
            amount_payable=json_fields.get("total"),
        ) if is_invoice else None,
        line_items=line_items_list if is_invoice else None,
        trade_fields=TradeFields(
            exporter=json_fields.get("exporter"),
            importer=json_fields.get("importer"),
            buyer=json_fields.get("buyer"),
            seller=json_fields.get("seller"),
            incoterms=json_fields.get("incoterms"),
            country_of_origin=json_fields.get("countryOfOrigin"),
            country_of_destination=json_fields.get("countryOfDestination"),
            port_of_loading=json_fields.get("portOfLoading"),
            port_of_discharge=json_fields.get("portOfDischarge"),
            gross_weight=json_fields.get("grossWeight"),
            net_weight=json_fields.get("netWeight"),
            payment_terms=json_fields.get("paymentTerms"),
            invoice_value=json_fields.get("invoiceValue"),
        ) if is_invoice else None,
        banking_info=BankingInfo(
            bank_name=json_fields.get("bankName"),
            branch_name=json_fields.get("branchName"),
            account_holder_name=json_fields.get("accountHolderName"),
            account_number=json_fields.get("accountNumber"),
            account_type=json_fields.get("accountType"),
            statement_period_from=json_fields.get("statementPeriodFrom"),
            statement_period_to=json_fields.get("statementPeriodTo"),
            currency=json_fields.get("currency"),
            opening_balance=json_fields.get("openingBalance"),
            closing_balance=json_fields.get("closingBalance"),
            transactions=[
                TransactionInfo(**txn) for txn in (json_fields.get("transactions") or [])
            ] if json_fields.get("transactions") else [],
        ) if is_banking else None,
        metadata=Metadata(
            page_count=ocr_pages,
            language=file_record.get("sourceLanguage"),
            file_type=file_record.get("mimeType"),
            uploaded_by=file_record.get("uploadedByName"),
            storage_path=file_record.get("_contentPath"),
        ),
        confidence_details=confidence,
        raw_ocr_text=raw_text,
        processing_metrics=ProcessingMetrics(
            ocr_engine=ocr_info.get("engine", "PaddleOCR"),
            extraction_engine=file_record.get("extractionMethod"),
            pages_processed=ocr_pages,
            fields_extracted=fields_extracted,
            tables_extracted=tables_count,
            average_confidence=round(base_confidence, 4),
            processing_time_seconds=processing_time,
            preprocessing_applied=bool(file_record.get("_preprocessed")),
            layout_analysis_applied=bool(layout_data.get("regions")),
            table_extraction_applied=tables_count > 0,
            validation_applied=bool(validation_data),
        ),
        validation_results=validation_results,
        layout_regions=layout_data.get("regions", []),
        extracted_tables=layout_data.get("tables", []),
    )


def build_ocr_only_json(file_record: dict[str, Any]) -> ExtractionJSON:
    ocr_info = file_record.get("ocr") or {}
    raw_text = file_record.get("extractedText") or ""
    base_confidence = file_record.get("confidence", 0.0) or 0.0
    layout_data = file_record.get("layoutAnalysis") or {}

    tables_count = len(layout_data.get("tables", []))

    return ExtractionJSON(
        document_id=file_record.get("id"),
        document_name=file_record.get("fileName"),
        status="ocr_only",
        ocr_engine=ocr_info.get("engine", "PaddleOCR"),
        overall_confidence=min(1.0, base_confidence),
        metadata=Metadata(
            page_count=ocr_info.get("pageCount", 1),
            language=file_record.get("sourceLanguage"),
            file_type=file_record.get("mimeType"),
            uploaded_by=file_record.get("uploadedByName"),
        ),
        raw_ocr_text=raw_text,
        processing_metrics=ProcessingMetrics(
            ocr_engine=ocr_info.get("engine", "PaddleOCR"),
            pages_processed=ocr_info.get("pageCount", 1),
            fields_extracted=0,
            tables_extracted=tables_count,
            average_confidence=round(base_confidence, 4),
        ),
        layout_regions=layout_data.get("regions", []),
        extracted_tables=layout_data.get("tables", []),
    )


def store_extraction_json(
    db: Session,
    scope: str,
    file_id: str,
    json_data: ExtractionJSON | dict[str, Any],
) -> ExtractionJSON:
    if isinstance(json_data, ExtractionJSON):
        json_dict = json_data.model_dump_export()
    else:
        json_dict = json_data

    store = get_state(db, scope, "extraction_json_store", {})
    if isinstance(json_data, ExtractionJSON):
        confidence_list = [c.model_dump() for c in json_data.confidence_details]
    else:
        confidence_list = json_dict.get("confidenceDetails", [])

    store[file_id] = {
        "json": json_dict,
        "confidenceDetails": confidence_list,
        "storedAt": now_iso(),
    }
    set_state(db, scope, "extraction_json_store", store)
    logger.info("extraction_json_stored file_id=%s status=%s", file_id, json_dict.get("status", "extracted"))
    return json_data if isinstance(json_data, ExtractionJSON) else ExtractionJSON(**json_dict)


def retrieve_extraction_json(
    db: Session,
    scope: str,
    file_id: str,
) -> ExtractionJSON | None:
    store = get_state(db, scope, "extraction_json_store", {})
    entry = store.get(file_id)
    if entry is None:
        return None
    json_dict = entry.get("json")
    if json_dict is None:
        return None
    try:
        return ExtractionJSON(**json_dict)
    except Exception as exc:
        logger.warning("retrieve_extraction_json_parse_error file_id=%s error=%s", file_id, exc)
        return None


def delete_extraction_json(db: Session, scope: str, file_id: str) -> None:
    store = get_state(db, scope, "extraction_json_store", {})
    if file_id in store:
        del store[file_id]
        set_state(db, scope, "extraction_json_store", store)
        logger.info("extraction_json_deleted file_id=%s", file_id)


def build_multi_page_result(
    documents: list[tuple[dict[str, Any], dict[str, Any]]],
) -> MultiPageDocument:
    docs = []
    for file_record, fields in documents:
        docs.append(build_extraction_json(file_record, fields))
    return MultiPageDocument(documents=docs)


def get_sap_field_mapping() -> dict[str, str]:
    return dict(SAP_FIELD_MAPPING)


def map_to_sap_fields(json_data: ExtractionJSON) -> dict[str, str | float | int]:
    mapping: dict[str, str | float | int] = {}
    flat = json_data.model_dump()
    for json_path, sap_field in SAP_FIELD_MAPPING.items():
        parts = json_path.replace("[]", "").split(".")
        value: object = flat
        try:
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part, "")
                else:
                    value = ""
                    break
            if value is not None and value != "" and value != 0:
                mapping[sap_field] = value
        except (KeyError, TypeError, IndexError):
            continue
    return mapping


def extract_clean_document_data(raw: dict[str, Any] | ExtractionJSON) -> dict[str, Any]:
    if isinstance(raw, ExtractionJSON):
        return raw.model_dump_clean_fields()

    data: dict[str, Any] = {}

    supplier = raw.get("supplier") or {}
    if isinstance(supplier, dict):
        cleaned = _strip_nulls(supplier)
        if cleaned:
            data["supplier"] = cleaned

    customer = raw.get("customer") or {}
    if isinstance(customer, dict):
        cleaned = _strip_nulls(customer)
        if cleaned:
            data["buyer"] = cleaned

    invoice = raw.get("invoice_details") or {}
    if isinstance(invoice, dict):
        invoice.pop("document_type", None)
        cleaned = _strip_nulls(invoice)
        if cleaned:
            data.update(cleaned)

    fin = raw.get("financial_summary") or {}
    if isinstance(fin, dict):
        cleaned = _strip_nulls(fin)
        if cleaned:
            data.update(cleaned)

    items = raw.get("line_items") or []
    if isinstance(items, list):
        clean_items = []
        for item in items:
            if isinstance(item, dict):
                item.pop("confidence", None)
                cleaned = _strip_nulls(item)
                if cleaned:
                    clean_items.append(cleaned)
            elif item:
                clean_items.append(item)
        if clean_items:
            data["line_items"] = clean_items

    return data


def json_to_bytes(json_data: ExtractionJSON | MultiPageDocument, indent: int = 2) -> bytes:
    if isinstance(json_data, MultiPageDocument):
        data = json_data.model_dump_export()
    else:
        data = json_data.model_dump_export()
    return json.dumps(data, indent=indent, default=str).encode("utf-8")
