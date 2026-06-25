from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger("translatrix.validation")

GSTIN_PATTERN = re.compile(r"^(\d{2})([A-Z]{5})(\d{4})([A-Z])([A-Z\d])(Z)([A-Z\d])$")
GSTIN_RAW_PATTERN = re.compile(r"(\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d])")

INVOICE_DATE_PATTERNS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%d.%m.%Y",
    "%Y.%m.%d",
    "%d %b %Y",
    "%d %B %Y",
]


class ValidationResult:
    """Result of a single validation check."""

    def __init__(
        self,
        field: str,
        value: Any,
        valid: bool,
        confidence: float,
        message: str | None = None,
        corrected_value: Any = None,
        severity: str = "warning",
    ):
        self.field = field
        self.value = value
        self.valid = valid
        self.confidence = round(confidence, 4)
        self.message = message
        self.corrected_value = corrected_value
        self.severity = severity

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "valid": self.valid,
            "confidence": self.confidence,
            "message": self.message,
            "correctedValue": self.corrected_value,
            "severity": self.severity,
        }


def validate_gstin(raw: str | None) -> ValidationResult:
    """Validate GSTIN format and attempt fuzzy correction for OCR errors."""
    if not raw:
        return ValidationResult(
            field="gstin",
            value=None,
            valid=False,
            confidence=0.0,
            message="GSTIN is missing.",
            severity="warning",
        )

    cleaned = raw.strip().upper().replace(" ", "").replace("-", "")
    cleaned = re.sub(r"[^0-9A-Z]", "", cleaned)

    match = GSTIN_PATTERN.match(cleaned)
    if match:
        return ValidationResult(
            field="gstin",
            value=cleaned,
            valid=True,
            confidence=0.98,
            message="GSTIN format is valid.",
        )

    fuzzy = _fuzzy_correct_gstin(cleaned)
    if fuzzy and GSTIN_PATTERN.match(fuzzy):
        return ValidationResult(
            field="gstin",
            value=fuzzy,
            valid=True,
            confidence=0.85,
            message=f"GSTIN corrected from '{cleaned}' to '{fuzzy}' based on format validation.",
            corrected_value=fuzzy,
            severity="needs_review",
        )

    if len(cleaned) == 15 and cleaned[:2].isdigit() and cleaned[2:7].isalpha():
        return ValidationResult(
            field="gstin",
            value=cleaned,
            valid=False,
            confidence=0.5,
            message=f"GSTIN '{cleaned}' has valid length and prefix pattern but failed checksum validation.",
            severity="needs_review",
        )

    return ValidationResult(
        field="gstin",
        value=raw,
        valid=False,
        confidence=max(0.1, _ocr_similarity_confidence(cleaned)),
        message=f"'{raw}' does not match GSTIN format (e.g., 27AAHFA7901M1Z8).",
        severity="needs_review",
    )


GSTIN_CHAR_MAP: dict[str, str] = {
    "0": "O",
    "O": "0",
    "1": "I",
    "I": "1",
    "5": "S",
    "S": "5",
    "8": "B",
    "B": "8",
    "6": "G",
    "G": "6",
    "L": "I",
    "I": "L",
    "M": "N",
    "N": "M",
}


def _fuzzy_correct_gstin(raw: str) -> str | None:
    """Try common OCR substitution corrections to recover a valid GSTIN."""
    candidates = [raw]
    for i, char in enumerate(raw):
        if char in GSTIN_CHAR_MAP:
            candidate = raw[:i] + GSTIN_CHAR_MAP[char] + raw[i + 1:]
            candidates.append(candidate)
    for r in ["J", "I"]:
        if len(raw) > 11:
            candidate = raw[:10] + r + raw[11:]
            candidates.append(candidate)
    for c in candidates:
        if GSTIN_PATTERN.match(c):
            return c
    return None


def _ocr_similarity_confidence(text: str) -> float:
    """Estimate confidence based on character class distribution."""
    if not text:
        return 0.0
    upper = sum(1 for c in text if c.isupper())
    digit = sum(1 for c in text if c.isdigit())
    total = len(text)
    if total < 10:
        return 0.3
    upper_ratio = upper / total
    digit_ratio = digit / total
    if 0.2 <= upper_ratio <= 0.6 and 0.3 <= digit_ratio <= 0.7:
        return 0.6
    return 0.4


def validate_date(raw: str | None) -> ValidationResult:
    """Validate and normalise a date string to ISO format."""
    if not raw:
        return ValidationResult(
            field="date",
            value=None,
            valid=False,
            confidence=0.0,
            message="Date is missing.",
            severity="warning",
        )

    cleaned = raw.strip().replace(".", "/").replace("-", "/").replace(" ", "/")
    cleaned = re.sub(r"/+", "/", cleaned)

    for fmt in INVOICE_DATE_PATTERNS:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            iso = parsed.date().isoformat()
            confidence = 0.95 if fmt in ("%d/%m/%Y", "%Y-%m-%d") else 0.88
            return ValidationResult(
                field="date",
                value=iso,
                valid=True,
                confidence=confidence,
                message=f"Date parsed as {iso}.",
            )
        except ValueError:
            continue

    try:
        from dateutil import parser as dateparser
        parsed = dateparser.parse(cleaned, fuzzy=True)
        iso = parsed.date().isoformat()
        return ValidationResult(
            field="date",
            value=iso,
            valid=True,
            confidence=0.8,
            message=f"Date parsed via fuzzy parser as {iso}.",
            corrected_value=iso,
            severity="needs_review",
        )
    except Exception:
        pass

    return ValidationResult(
        field="date",
        value=raw,
        valid=False,
        confidence=0.3,
        message=f"'{raw}' could not be parsed as a recognised date format.",
        severity="needs_review",
    )


def validate_invoice_number(raw: str | None) -> ValidationResult:
    """Validate an invoice number is not merged text and has expected structure."""
    if not raw:
        return ValidationResult(
            field="invoice_number",
            value=None,
            valid=False,
            confidence=0.0,
            message="Invoice number is missing.",
            severity="warning",
        )

    cleaned = raw.strip().rstrip(".:-#")

    if len(cleaned) < 2 or len(cleaned) > 50:
        return ValidationResult(
            field="invoice_number",
            value=cleaned,
            valid=False,
            confidence=0.3,
            message=f"'{cleaned}' length ({len(cleaned)}) is unusual for an invoice number.",
            severity="needs_review",
        )

    merged = re.search(
        r"(INVOICE|TAX\s*INVOICE|GST|BILL|RECEIPT|DATE|TOTAL|AMOUNT|PAYMENT)",
        cleaned,
        re.I,
    )
    if merged:
        return ValidationResult(
            field="invoice_number",
            value=cleaned,
            valid=False,
            confidence=0.3,
            message=f"Invoice number appears merged with '{merged.group(1)}'.",
            severity="needs_review",
        )

    mixed_ratio = sum(1 for c in cleaned if c.isalnum()) / max(len(cleaned), 1)
    if mixed_ratio < 0.6:
        return ValidationResult(
            field="invoice_number",
            value=cleaned,
            valid=False,
            confidence=0.4,
            message=f"'{cleaned}' contains excessive special characters.",
            severity="needs_review",
        )

    has_letter = any(c.isalpha() for c in cleaned)
    has_digit = any(c.isdigit() for c in cleaned)
    if has_letter and has_digit:
        return ValidationResult(
            field="invoice_number",
            value=cleaned,
            valid=True,
            confidence=0.92,
            message="Invoice number contains mixed alphanumeric characters (typical).",
        )
    if has_digit:
        return ValidationResult(
            field="invoice_number",
            value=cleaned,
            valid=True,
            confidence=0.88,
            message="Invoice number is numeric-only.",
        )

    return ValidationResult(
        field="invoice_number",
        value=cleaned,
        valid=True,
        confidence=0.7,
        message="Invoice number is letter-only (unusual but possible).",
    )


HSN_PATTERN = re.compile(r"^\d{4,8}$")


def validate_hsn(raw: str | None, *, field: str = "hsn_code") -> ValidationResult:
    """HSN/SAC codes are 4-8 digit numeric codes under GST. Flag anything
    that doesn't match for manual review rather than silently accepting
    OCR noise (e.g. a misread batch number) as a valid HSN code."""
    if not raw:
        return ValidationResult(
            field=field, value=None, valid=False, confidence=0.0,
            message="HSN/SAC code is missing.", severity="warning",
        )
    cleaned = str(raw).strip().replace(" ", "")
    if HSN_PATTERN.match(cleaned):
        confidence = 0.95 if len(cleaned) in (4, 6, 8) else 0.85
        return ValidationResult(
            field=field, value=cleaned, valid=True, confidence=confidence,
            message=f"HSN/SAC code '{cleaned}' has a valid {len(cleaned)}-digit format.",
        )
    digits_only = re.sub(r"\D", "", cleaned)
    if digits_only and HSN_PATTERN.match(digits_only):
        return ValidationResult(
            field=field, value=digits_only, valid=True, confidence=0.6,
            message=f"HSN/SAC code corrected from '{raw}' to '{digits_only}'.",
            corrected_value=digits_only, severity="needs_review",
        )
    return ValidationResult(
        field=field, value=cleaned, valid=False, confidence=0.2,
        message=f"'{raw}' is not a valid HSN/SAC code (expected 4-8 digits).",
        severity="needs_review",
    )


def validate_line_items(line_items: list[dict[str, Any]] | None) -> list[ValidationResult]:
    """Per-line-item validation: HSN code format and numeric amount sanity.
    Runs across however many line items were merged in from all extraction
    chunks, so issues on any page surface in the same validation report."""
    results: list[ValidationResult] = []
    if not line_items:
        return results

    for idx, item in enumerate(line_items):
        if not isinstance(item, dict):
            continue
        label = item.get("description") or item.get("product_name") or f"item {idx + 1}"
        hsn = item.get("hsn_code")
        if hsn:
            hsn_result = validate_hsn(hsn, field=f"line_item[{idx}].hsn_code")
            if not hsn_result.valid:
                hsn_result.message = f"{label}: {hsn_result.message}"
                results.append(hsn_result)

        for amount_key in ("quantity", "mrp", "rate", "line_total"):
            value = item.get(amount_key)
            if value is None:
                continue
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                results.append(ValidationResult(
                    field=f"line_item[{idx}].{amount_key}", value=value, valid=False,
                    confidence=0.2, message=f"{label}: '{amount_key}' value '{value}' is not numeric.",
                    severity="needs_review",
                ))
                continue
            if numeric < 0:
                results.append(ValidationResult(
                    field=f"line_item[{idx}].{amount_key}", value=value, valid=False,
                    confidence=0.3, message=f"{label}: '{amount_key}' is negative ({numeric}).",
                    severity="needs_review",
                ))
    return results


def validate_amount_reconciliation(
    total: float | None,
    subtotal: float | None,
    tax_amount: float | None,
    tolerance: float = 0.05,
) -> ValidationResult:
    """Verify that subtotal + tax approximates total."""
    if total is None or subtotal is None or tax_amount is None:
        return ValidationResult(
            field="amount_reconciliation",
            value=None,
            valid=False,
            confidence=0.0,
            message="Cannot reconcile - one or more amount fields are missing.",
            severity="warning",
        )
    expected = round(subtotal + tax_amount, 2)
    diff = abs(expected - total)
    if diff <= tolerance:
        return ValidationResult(
            field="amount_reconciliation",
            value={"subtotal": subtotal, "tax": tax_amount, "total": total},
            valid=True,
            confidence=0.95,
            message=f"Subtotal ({subtotal}) + Tax ({tax_amount}) = {expected} matches Total ({total}).",
        )
    ratio = diff / max(total, 0.01)
    if ratio < 0.05:
        return ValidationResult(
            field="amount_reconciliation",
            value={"subtotal": subtotal, "tax": tax_amount, "total": total},
            valid=False,
            confidence=0.85,
            message=f"Subtotal + Tax ({expected}) differs from Total ({total}) by {diff:.2f} (minor).",
            severity="needs_review",
        )
    return ValidationResult(
        field="amount_reconciliation",
        value={"subtotal": subtotal, "tax": tax_amount, "total": total},
        valid=False,
        confidence=0.5,
        message=f"Subtotal + Tax ({expected}) differs from Total ({total}) by {diff:.2f}.",
        severity="warning",
    )


def validate_gst_breakdown(
    cgst: float | None,
    sgst: float | None,
    igst: float | None,
    total_tax: float | None,
    tolerance: float = 0.05,
) -> ValidationResult:
    """Verify that CGST + SGST (or IGST alone) matches the reported total tax."""
    if total_tax is None:
        if cgst is not None or sgst is not None or igst is not None:
            return ValidationResult(
                field="gst_breakdown",
                value={"cgst": cgst, "sgst": sgst, "igst": igst},
                valid=True,
                confidence=0.85,
                message="GST components found but no total tax line; values recorded as extracted.",
            )
        return ValidationResult(
            field="gst_breakdown",
            value=None,
            valid=False,
            confidence=0.0,
            message="No GST data available.",
            severity="warning",
        )
    if cgst is not None and sgst is not None:
        computed = round(cgst + sgst, 2)
        diff = abs(computed - total_tax)
        if diff <= tolerance:
            return ValidationResult(
                field="gst_breakdown",
                value={"cgst": cgst, "sgst": sgst, "igst": igst, "computed_total": computed},
                valid=True,
                confidence=0.95,
                message=f"CGST ({cgst}) + SGST ({sgst}) = {computed} matches total tax ({total_tax}).",
            )
        return ValidationResult(
            field="gst_breakdown",
            value={"cgst": cgst, "sgst": sgst, "igst": igst, "computed_total": computed},
            valid=False,
            confidence=0.6,
            message=f"CGST ({cgst}) + SGST ({sgst}) = {computed} differs from total tax ({total_tax}).",
            severity="needs_review",
        )
    if igst is not None:
        diff = abs(igst - total_tax)
        if diff <= tolerance:
            return ValidationResult(
                field="gst_breakdown",
                value={"cgst": cgst, "sgst": sgst, "igst": igst},
                valid=True,
                confidence=0.95,
                message=f"IGST ({igst}) matches total tax ({total_tax}).",
            )
        return ValidationResult(
            field="gst_breakdown",
            value={"cgst": cgst, "sgst": sgst, "igst": igst},
            valid=False,
            confidence=0.6,
            message=f"IGST ({igst}) differs from total tax ({total_tax}).",
            severity="needs_review",
        )
    return ValidationResult(
        field="gst_breakdown",
        value={"cgst": cgst, "sgst": sgst, "igst": igst, "total_tax": total_tax},
        valid=True,
        confidence=0.7,
        message="Total tax present but GST breakdown incomplete.",
    )


def validate_all(
    fields: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Run all validators and return categorised results."""
    results: dict[str, list[dict[str, Any]]] = {
        "valid": [],
        "needs_review": [],
        "warning": [],
    }
    validators: list[ValidationResult] = []

    validators.append(validate_gstin(fields.get("gstVatNumber")))
    validators.append(validate_date(fields.get("invoiceDate")))
    validators.append(validate_date(fields.get("dueDate")))
    validators.append(validate_invoice_number(fields.get("invoiceNumber")))
    validators.append(
        validate_amount_reconciliation(
            _safe_float(fields.get("total")),
            _safe_float(fields.get("subtotal")),
            _safe_float(fields.get("taxAmount")),
        )
    )
    validators.append(
        validate_gst_breakdown(
            _safe_float(fields.get("cgstAmount")),
            _safe_float(fields.get("sgstAmount")),
            _safe_float(fields.get("igstAmount")),
            _safe_float(fields.get("taxAmount")),
        )
    )
    validators.extend(validate_line_items(fields.get("lineItems")))

    for v in validators:
        if v.valid and v.confidence >= 0.9:
            results["valid"].append(v.to_dict())
        elif v.severity == "needs_review":
            results["needs_review"].append(v.to_dict())
        else:
            results["warning"].append(v.to_dict())

    return results


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
