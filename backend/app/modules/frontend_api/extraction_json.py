from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SupplierInfo(BaseModel):
    name: str | None = None
    gstin: str | None = None
    pan: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None


class CustomerInfo(BaseModel):
    name: str | None = None
    pan: str | None = None
    gstin: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None


class InvoiceDetails(BaseModel):
    invoice_number: str | None = None
    invoice_date: str | None = None
    document_type: str | None = None
    currency: str | None = None


class FinancialSummary(BaseModel):
    gross_amount: float | None = None
    net_amount: float | None = None
    gst_amount: float | None = None
    cgst_amount: float | None = None
    sgst_amount: float | None = None
    igst_amount: float | None = None
    discount_amount: float | None = None
    taxable_value: float | None = None
    place_of_supply: str | None = None
    reverse_charge: bool | None = None
    amount_payable: float | None = None


class TradeFields(BaseModel):
    exporter: str | None = None
    importer: str | None = None
    buyer: str | None = None
    seller: str | None = None
    incoterms: str | None = None
    country_of_origin: str | None = None
    country_of_destination: str | None = None
    port_of_loading: str | None = None
    port_of_discharge: str | None = None
    gross_weight: float | None = None
    net_weight: float | None = None
    payment_terms: str | None = None
    invoice_value: float | None = None


class TransactionInfo(BaseModel):
    transaction_date: str | None = None
    reference_date: str | None = None
    transaction_code: str | None = None
    particulars: str | None = None
    cheque_number: str | None = None
    debit_amount: float | None = None
    credit_amount: float | None = None
    running_balance: float | None = None
    balance_type: str | None = None


class BankingInfo(BaseModel):
    bank_name: str | None = None
    branch_name: str | None = None
    account_holder_name: str | None = None
    account_number: str | None = None
    account_type: str | None = None
    statement_period_from: str | None = None
    statement_period_to: str | None = None
    currency: str | None = None
    opening_balance: float | None = None
    closing_balance: float | None = None
    transactions: list[TransactionInfo] = Field(default_factory=list)


class LineItem(BaseModel):
    product_name: str | None = None
    hsn_code: str | None = None
    pack: str | None = None
    batch_number: str | None = None
    expiry_date: str | None = None
    quantity: float | None = None
    mrp: float | None = None
    rate: float | None = None
    gst: float | None = None
    taxable_value: float | None = None
    cgst: float | None = None
    sgst: float | None = None
    igst: float | None = None
    line_total: float | None = None
    confidence: float | None = None


class Metadata(BaseModel):
    page_count: int | None = None
    language: str | None = None
    file_type: str | None = None
    uploaded_by: str | None = None
    storage_path: str | None = None


class FieldConfidence(BaseModel):
    field: str
    value: Any = None
    confidence: float = 0.0
    status: str = "missing"
    source: str | None = None
    page: int | None = None


class ProcessingMetrics(BaseModel):
    ocr_engine: str | None = None
    extraction_engine: str | None = None
    pages_processed: int | None = None
    fields_extracted: int | None = None
    tables_extracted: int | None = None
    average_confidence: float | None = None
    processing_time_seconds: float | None = None
    preprocessing_applied: bool = False
    layout_analysis_applied: bool = False
    table_extraction_applied: bool = False
    validation_applied: bool = False


class ValidationResult(BaseModel):
    field: str
    value: Any = None
    valid: bool = False
    confidence: float = 0.0
    message: str | None = None
    corrected_value: Any = None
    severity: str = "warning"


class ExtractionJSON(BaseModel):
    model_config = ConfigDict(extra="ignore")

    document_id: str | None = None
    document_type: str | None = None
    document_name: str | None = None
    processing_timestamp: str | None = None
    ocr_engine: str | None = None
    overall_confidence: float | None = None
    status: str = "extracted"
    supplier: SupplierInfo | None = None
    customer: CustomerInfo | None = None
    invoice_details: InvoiceDetails | None = None
    financial_summary: FinancialSummary | None = None
    line_items: list[LineItem] | None = None
    trade_fields: TradeFields | None = None
    banking_info: BankingInfo | None = None
    metadata: Metadata = Field(default_factory=Metadata)
    confidence_details: list[FieldConfidence] = Field(default_factory=list)
    raw_ocr_text: str | None = None
    processing_metrics: ProcessingMetrics = Field(default_factory=ProcessingMetrics)
    validation_results: list[ValidationResult] = Field(default_factory=list)
    layout_regions: list[dict[str, Any]] = Field(default_factory=list)
    extracted_tables: list[dict[str, Any]] = Field(default_factory=list)

    def model_dump_export(self) -> dict[str, Any]:
        return self.model_dump()

    def model_dump_export_clean(self) -> dict[str, Any]:
        return self.model_dump(exclude={"confidence_details"})

    def model_dump_debug(self) -> dict[str, Any]:
        return self.model_dump()

    def model_dump_clean_fields(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.supplier:
            supplier = _strip_nulls(self.supplier.model_dump())
            if supplier:
                data["supplier"] = supplier
        if self.customer:
            buyer = _strip_nulls(self.customer.model_dump())
            if buyer:
                data["buyer"] = buyer
        if self.invoice_details:
            invoice = _strip_nulls(self.invoice_details.model_dump(exclude={"document_type"}))
            if invoice:
                data.update(invoice)
        if self.financial_summary:
            fin = _strip_nulls(self.financial_summary.model_dump())
            if fin:
                data.update(fin)
        clean_items = []
        for item in self.line_items:
            clean = _strip_nulls(item.model_dump(exclude={"confidence"}) if item else {})
            if clean:
                clean_items.append(clean)
        if clean_items:
            data["line_items"] = clean_items
        return data


def _strip_nulls(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {k: _strip_nulls(v) for k, v in value.items() if v is not None and v != "" and v != [] and v != {}}
        return cleaned if cleaned else None
    if isinstance(value, list):
        cleaned = [_strip_nulls(v) for v in value if v is not None and v != "" and v != [] and v != {}]
        cleaned = [v for v in cleaned if v is not None]
        return cleaned if cleaned else None
    return value


class MultiPageDocument(BaseModel):
    documents: list[ExtractionJSON] = Field(default_factory=list)

    def model_dump_export(self) -> dict[str, Any]:
        return {"documents": [d.model_dump_export() for d in self.documents]}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
